#!/usr/bin/env python3
"""Reconcile medical bills against insurer Explanation of Benefits (EOB) lines.

Stdlib only. Two subcommands:

  validate  --eob eob_lines.csv [--bills bill_lines.csv]
      Check column names, dates, money values, and EOB arithmetic. Exit 1 on errors.

  run       --eob eob_lines.csv --bills bill_lines.csv --out DIR
            [--as-of YYYY-MM-DD] [--no-eob-days 45] [--tolerance 1.00]
            [--aliases providers.csv] [--deductible N] [--oop-max N]
      Write matches.csv, exceptions.csv, and summary.json into DIR.

Nothing here contacts a portal, insurer, or provider. It only reads CSV files.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

EOB_COLUMNS = [
    "claim_id", "service_date", "provider", "patient", "cpt", "billed", "allowed",
    "plan_paid", "patient_resp", "deductible_applied", "coinsurance", "copay",
    "eob_date", "source_file", "source_page",
]
BILL_COLUMNS = [
    "bill_id", "statement_date", "service_date", "provider", "patient", "cpt",
    "billed", "amount_due", "claim_id", "source_file", "source_page",
]
EOB_REQUIRED = ["service_date", "provider", "patient", "billed", "allowed", "plan_paid",
                "patient_resp", "source_file"]
BILL_REQUIRED = ["bill_id", "statement_date", "service_date", "provider", "patient",
                 "amount_due", "source_file"]
EOB_MONEY = ["billed", "allowed", "plan_paid", "patient_resp", "deductible_applied",
             "coinsurance", "copay"]
BILL_MONEY = ["billed", "amount_due"]
PROVIDER_NOISE = {
    "llc", "pllc", "pc", "pa", "inc", "md", "do", "dds", "corp", "co", "ltd",
    "the", "group", "associates", "assoc", "and",
}
ZERO = Decimal("0")


class InputError(Exception):
    pass


def parse_money(value: str) -> Decimal:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if text == "" or text == "-":
        return ZERO
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"not a money value: {value!r}") from exc
    return -amount if negative else amount


def parse_date(value: str) -> date:
    text = (value or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        return date(int(m[3]), int(m[1]), int(m[2]))
    raise ValueError(f"not a date (use YYYY-MM-DD or MM/DD/YYYY): {value!r}")


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (value or "").lower())).strip()


def norm_provider(value: str, aliases: dict[str, str]) -> str:
    base = norm_text(value)
    if base in aliases:
        return aliases[base]
    words = [w for w in base.split() if w not in PROVIDER_NOISE]
    key = " ".join(words) or base
    return aliases.get(key, key)


def load_aliases(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    aliases: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"alias", "canonical"} <= set(reader.fieldnames):
            raise InputError(f"{path}: alias file needs columns alias,canonical")
        for row in reader:
            canonical = norm_text(row["canonical"])
            aliases[norm_text(row["alias"])] = canonical
            aliases[canonical] = canonical
    return aliases


@dataclass
class Line:
    kind: str
    row_number: int
    raw: dict[str, str]
    money: dict[str, Decimal] = field(default_factory=dict)
    service_date: date | None = None
    statement_date: date | None = None
    provider_key: str = ""
    patient_key: str = ""

    def ref(self) -> str:
        page = self.raw.get("source_page") or "?"
        return f"{self.raw.get('source_file', '?')} p{page} (row {self.row_number})"


def read_lines(path: Path, kind: str, aliases: dict[str, str]) -> tuple[list[Line], list[str]]:
    required = EOB_REQUIRED if kind == "eob" else BILL_REQUIRED
    known = EOB_COLUMNS if kind == "eob" else BILL_COLUMNS
    money_cols = EOB_MONEY if kind == "eob" else BILL_MONEY
    errors: list[str] = []
    lines: list[Line] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in required if c not in header]
        if missing:
            raise InputError(f"{path}: missing required columns: {', '.join(missing)}")
        unknown = [c for c in header if c not in known]
        if unknown:
            errors.append(f"{path}: unknown columns ignored: {', '.join(unknown)}")
        for index, raw in enumerate(reader, start=2):
            row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
            if not any(row.values()):
                continue
            line = Line(kind=kind, row_number=index, raw=row)
            for col in required:
                if not row.get(col):
                    errors.append(f"{path} row {index}: empty required field {col}")
            for col in money_cols:
                try:
                    line.money[col] = parse_money(row.get(col, ""))
                except ValueError as exc:
                    errors.append(f"{path} row {index}: {col}: {exc}")
            try:
                line.service_date = parse_date(row.get("service_date", ""))
            except ValueError as exc:
                errors.append(f"{path} row {index}: service_date: {exc}")
            if kind == "bill":
                try:
                    line.statement_date = parse_date(row.get("statement_date", ""))
                except ValueError as exc:
                    errors.append(f"{path} row {index}: statement_date: {exc}")
            line.provider_key = norm_provider(row.get("provider", ""), aliases)
            line.patient_key = norm_text(row.get("patient", ""))
            lines.append(line)
    return lines, errors


def eob_math_issues(line: Line, tolerance: Decimal) -> list[str]:
    m = line.money
    issues = []
    if any(col not in m for col in ("billed", "allowed", "plan_paid", "patient_resp")):
        return issues  # a money parse error is already reported for this row
    if m.get("allowed", ZERO) > m.get("billed", ZERO) + tolerance:
        issues.append(f"allowed {m['allowed']} exceeds billed {m['billed']}")
    gap = m.get("allowed", ZERO) - m.get("plan_paid", ZERO) - m.get("patient_resp", ZERO)
    if abs(gap) > tolerance:
        issues.append(
            f"allowed {m['allowed']} != plan_paid {m['plan_paid']} + patient_resp "
            f"{m['patient_resp']} (gap {gap})"
        )
    return issues


def is_warning(message: str) -> bool:
    return "unknown columns ignored" in message


def cmd_validate(args: argparse.Namespace) -> int:
    aliases = load_aliases(args.aliases)
    tolerance = Decimal(str(args.tolerance))
    problems: list[str] = []
    eob, errs = read_lines(args.eob, "eob", aliases)
    problems += errs
    for line in eob:
        for issue in eob_math_issues(line, tolerance):
            problems.append(f"EOB_MATH {line.ref()}: {issue}")
    bills: list[Line] = []
    if args.bills:
        bills, errs = read_lines(args.bills, "bill", aliases)
        problems += errs
    hard = [p for p in problems if not is_warning(p)]
    for p in problems:
        print(("WARN " if is_warning(p) else "ERROR ") + p)
    status = "FAIL" if hard else "PASS"
    print(f"VALIDATION={status} eob_lines={len(eob)} bill_lines={len(bills)} errors={len(hard)}")
    return 1 if hard else 0


def match_key(line: Line) -> tuple:
    return (line.patient_key, line.service_date, line.provider_key)


def cpt_compatible(a: Line, b: Line) -> bool:
    ca, cb = norm_text(a.raw.get("cpt", "")), norm_text(b.raw.get("cpt", ""))
    return not ca or not cb or ca == cb


def cmd_run(args: argparse.Namespace) -> int:
    aliases = load_aliases(args.aliases)
    tolerance = Decimal(str(args.tolerance))
    as_of = parse_date(args.as_of) if args.as_of else date.today()
    eob, eob_errs = read_lines(args.eob, "eob", aliases)
    bills, bill_errs = read_lines(args.bills, "bill", aliases)
    hard = [e for e in eob_errs + bill_errs if not is_warning(e)]
    if hard:
        for e in hard:
            print("ERROR " + e, file=sys.stderr)
        print("RECONCILE=FAIL reason=invalid_input (run the validate subcommand)", file=sys.stderr)
        return 1

    exceptions: list[dict[str, str]] = []

    def flag(code: str, line: Line, detail: str, amount: Decimal | None = None) -> None:
        exceptions.append({
            "code": code,
            "kind": line.kind,
            "patient": line.raw.get("patient", ""),
            "service_date": line.raw.get("service_date", ""),
            "provider": line.raw.get("provider", ""),
            "cpt": line.raw.get("cpt", ""),
            "claim_id": line.raw.get("claim_id", ""),
            "bill_id": line.raw.get("bill_id", ""),
            "amount": f"{amount:.2f}" if amount is not None else "",
            "detail": detail,
            "source": line.ref(),
        })

    for line in eob:
        for issue in eob_math_issues(line, tolerance):
            flag("EOB_MATH", line, issue)

    # Same service processed under two different claim numbers.
    seen: dict[tuple, Line] = {}
    for line in eob:
        key = match_key(line) + (norm_text(line.raw.get("cpt", "")), line.money["billed"])
        prior = seen.get(key)
        if prior and prior.raw.get("claim_id") != line.raw.get("claim_id"):
            flag("DUPLICATE_CLAIM", line,
                 f"same service also on claim {prior.raw.get('claim_id') or '?'} ({prior.ref()})",
                 line.money["patient_resp"])
        else:
            seen.setdefault(key, line)

    # Same charge listed twice on one statement.
    seen_bill: dict[tuple, Line] = {}
    for line in bills:
        key = (line.raw["bill_id"], line.statement_date) + match_key(line) + (
            norm_text(line.raw.get("cpt", "")), line.money["billed"], line.money["amount_due"])
        if key in seen_bill:
            flag("DUPLICATE_CHARGE", line,
                 f"identical line already on this statement ({seen_bill[key].ref()})",
                 line.money["amount_due"])
        else:
            seen_bill[key] = line

    by_claim: dict[str, list[Line]] = defaultdict(list)
    by_key: dict[tuple, list[Line]] = defaultdict(list)
    for line in eob:
        if line.raw.get("claim_id"):
            by_claim[norm_text(line.raw["claim_id"])].append(line)
        by_key[match_key(line)].append(line)

    matches: list[dict[str, str]] = []
    for bill in bills:
        claim = norm_text(bill.raw.get("claim_id", ""))
        candidates = by_claim.get(claim, []) if claim else []
        method = "claim_id"
        if candidates and bill.raw.get("cpt"):
            narrowed = [c for c in candidates if cpt_compatible(bill, c)]
            candidates = narrowed or candidates
        if not candidates:
            method = "date_provider_patient"
            candidates = [c for c in by_key.get(match_key(bill), []) if cpt_compatible(bill, c)]
            if bill.money["billed"] and len(candidates) > 1:
                exact = [c for c in candidates if abs(c.money["billed"] - bill.money["billed"]) <= tolerance]
                candidates = exact or candidates
        if not candidates:
            age = (as_of - bill.statement_date).days if bill.statement_date else 0
            if age >= args.no_eob_days:
                flag("NO_EOB", bill, f"no EOB found; statement is {age} days old",
                     bill.money["amount_due"])
            else:
                flag("NO_EOB_PENDING", bill,
                     f"no EOB yet; statement is {age} days old (threshold {args.no_eob_days})",
                     bill.money["amount_due"])
            continue
        owed = sum((c.money["patient_resp"] for c in candidates), ZERO)
        due = bill.money["amount_due"]
        diff = due - owed
        status = "OK"
        if diff > tolerance:
            status = "OVERBILLED"
            flag("OVERBILLED", bill,
                 f"bill asks {due} but EOB patient responsibility is {owed}",
                 diff)
        elif diff < -tolerance:
            status = "BILL_BELOW_EOB"
            flag("BILL_BELOW_EOB", bill,
                 f"bill asks {due}, EOB says {owed}; may reflect a payment already made", -diff)
        if bill.money["billed"] and candidates:
            eob_billed = sum((c.money["billed"] for c in candidates), ZERO)
            if abs(eob_billed - bill.money["billed"]) > tolerance:
                flag("BILLED_MISMATCH", bill,
                     f"provider billed {bill.money['billed']} on statement but {eob_billed} on EOB")
        matches.append({
            "bill_id": bill.raw["bill_id"],
            "statement_date": bill.raw["statement_date"],
            "service_date": bill.raw["service_date"],
            "provider": bill.raw["provider"],
            "patient": bill.raw["patient"],
            "amount_due": f"{due:.2f}",
            "eob_patient_resp": f"{owed:.2f}",
            "difference": f"{diff:.2f}",
            "status": status,
            "method": method,
            "claim_ids": ";".join(sorted({c.raw.get("claim_id", "") for c in candidates})),
            "bill_source": bill.ref(),
            "eob_sources": " | ".join(c.ref() for c in candidates),
        })

    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: ZERO))
    for line in eob:
        t = totals[line.raw["patient"]]
        for col in EOB_MONEY:
            t[col] += line.money.get(col, ZERO)
    accumulators = {}
    for patient, t in totals.items():
        acc = {k: f"{v:.2f}" for k, v in t.items()}
        if args.deductible is not None:
            ded = Decimal(str(args.deductible))
            acc["deductible_remaining"] = f"{max(ded - t['deductible_applied'], ZERO):.2f}"
            if t["deductible_applied"] > ded + tolerance:
                exceptions.append({"code": "DEDUCTIBLE_EXCEEDED", "kind": "summary",
                                   "patient": patient, "amount": f"{t['deductible_applied'] - ded:.2f}",
                                   "detail": f"deductible applied {t['deductible_applied']} exceeds plan deductible {ded}"})
        if args.oop_max is not None:
            oop = Decimal(str(args.oop_max))
            acc["oop_remaining"] = f"{max(oop - t['patient_resp'], ZERO):.2f}"
            if t["patient_resp"] > oop + tolerance:
                exceptions.append({"code": "OOP_MAX_EXCEEDED", "kind": "summary",
                                   "patient": patient, "amount": f"{t['patient_resp'] - oop:.2f}",
                                   "detail": f"patient responsibility {t['patient_resp']} exceeds out-of-pocket max {oop}"})
        accumulators[patient] = acc

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    match_cols = ["bill_id", "statement_date", "service_date", "provider", "patient", "amount_due",
                  "eob_patient_resp", "difference", "status", "method", "claim_ids",
                  "bill_source", "eob_sources"]
    exc_cols = ["code", "kind", "patient", "service_date", "provider", "cpt", "claim_id", "bill_id",
                "amount", "detail", "source"]
    with (out / "matches.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=match_cols)
        writer.writeheader()
        writer.writerows(matches)
    with (out / "exceptions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=exc_cols, restval="")
        writer.writeheader()
        writer.writerows(exceptions)
    counts: dict[str, int] = defaultdict(int)
    for e in exceptions:
        counts[e["code"]] += 1
    summary = {
        "as_of": as_of.isoformat(),
        "eob_lines": len(eob),
        "bill_lines": len(bills),
        "matched_bill_lines": len(matches),
        "exceptions": dict(sorted(counts.items())),
        "accumulators": accumulators,
        "warnings": [e for e in eob_errs + bill_errs if is_warning(e)],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"RECONCILE=PASS matched={len(matches)} exceptions={len(exceptions)} out={out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check input CSVs")
    v.add_argument("--eob", type=Path, required=True)
    v.add_argument("--bills", type=Path)
    v.add_argument("--aliases", type=Path)
    v.add_argument("--tolerance", default="1.00")
    v.set_defaults(func=cmd_validate)
    r = sub.add_parser("run", help="reconcile bills against EOB lines")
    r.add_argument("--eob", type=Path, required=True)
    r.add_argument("--bills", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--as-of")
    r.add_argument("--no-eob-days", type=int, default=45)
    r.add_argument("--tolerance", default="1.00")
    r.add_argument("--aliases", type=Path)
    r.add_argument("--deductible", type=Decimal)
    r.add_argument("--oop-max", type=Decimal)
    r.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
