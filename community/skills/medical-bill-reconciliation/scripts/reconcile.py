#!/usr/bin/env python3
"""Reconcile medical bills against insurer Explanation of Benefits (EOB) lines.

Stdlib only. Two subcommands:

  validate  --eob eob_lines.csv [--bills bill_lines.csv]
      Check column names, dates, money values, and EOB arithmetic. Exit 1 on errors.

  run       --eob eob_lines.csv --bills bill_lines.csv --out DIR
            [--as-of YYYY-MM-DD] [--no-eob-days 45] [--tolerance 1.00]  # pass --as-of for repeatable output
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
    text = (value or "").lower()
    # Collapse dotted initials so "P.A.", "M.D.", "L.L.C." become "pa", "md", "llc".
    text = re.sub(r"(?<=\b[a-z])\.", "", text)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text)).strip()


def provider_core(value: str) -> str:
    base = norm_text(value)
    words = [w for w in base.split() if w not in PROVIDER_NOISE]
    return " ".join(words) or base


def norm_provider(value: str, aliases: dict[str, str]) -> str:
    core = provider_core(value)
    return aliases.get(core, core)


def cpt_base(value: str) -> str:
    """Base procedure code: modifiers and unit suffixes ("99213-25", "99213 x2") are ignored."""
    return re.sub(r"[^A-Za-z0-9]", "", value or "")[:5].upper()


def load_aliases(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    aliases: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"alias", "canonical"} <= {f.strip() for f in reader.fieldnames}:
            raise InputError(f"{path}: alias file needs columns alias,canonical")
        for raw in reader:
            row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
            if not row.get("alias") or not row.get("canonical"):
                raise InputError(f"{path} row {reader.line_num}: alias and canonical are both required")
            canonical = provider_core(row["canonical"])
            aliases[provider_core(row["alias"])] = canonical
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
    eob_date: date | None = None
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
            if kind == "eob" and row.get("eob_date"):
                try:
                    line.eob_date = parse_date(row["eob_date"])
                except ValueError as exc:
                    errors.append(f"{path} row {index}: eob_date: {exc}")
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
    ca, cb = cpt_base(a.raw.get("cpt", "")), cpt_base(b.raw.get("cpt", ""))
    return not ca or not cb or ca == cb


def money_arg(text: str) -> Decimal:
    try:
        value = Decimal(str(text).replace("$", "").replace(",", ""))
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}")
    if not value.is_finite() or value < 0:
        raise argparse.ArgumentTypeError(f"must be a non-negative number: {text!r}")
    return value


def date_arg(text: str) -> date:
    try:
        return parse_date(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))


def cmd_run(args: argparse.Namespace) -> int:
    aliases = load_aliases(args.aliases)
    tolerance: Decimal = args.tolerance
    as_of: date = args.as_of or date.today()
    eob, eob_errs = read_lines(args.eob, "eob", aliases)
    bills, bill_errs = read_lines(args.bills, "bill", aliases)
    hard = [e for e in eob_errs + bill_errs if not is_warning(e)]
    if hard:
        for e in hard:
            print("ERROR " + e, file=sys.stderr)
        print("RECONCILE=FAIL reason=invalid_input (run the validate subcommand)", file=sys.stderr)
        return 1

    exceptions: list[dict[str, str]] = []

    def flag(code: str, line: Line, detail: str, amount: Decimal | None = None,
             source: str | None = None) -> None:
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
            "source": source or line.ref(),
        })

    for line in eob:
        for issue in eob_math_issues(line, tolerance):
            flag("EOB_MATH", line, issue)

    # ---- EOB de-duplication. Excluded lines never reach matching or accumulators.
    # A claim line's identity ignores the money split, so a corrected EOB that changes
    # allowed/paid/responsibility is recognised as the same line, not a second one.
    order = {id(line): i for i, line in enumerate(eob)}
    identities: dict[tuple, list[Line]] = defaultdict(list)
    for line in eob:
        identity = ((norm_text(line.raw.get("claim_id", "")),) + match_key(line)
                    + (cpt_base(line.raw.get("cpt", "")), line.money["billed"]))
        identities[identity].append(line)
    excluded: set[int] = set()
    excluded_as: dict[str, str] = {}
    for copies in identities.values():
        files = list(dict.fromkeys(c.raw.get("source_file", "") for c in copies))
        if len(files) > 1:
            # Keep the document with the latest eob_date; ties go to the one loaded last.
            def rank(name: str, copies: list[Line] = copies) -> tuple:
                mine = [c for c in copies if c.raw.get("source_file", "") == name]
                dates = [c.eob_date for c in mine if c.eob_date]
                return (max(dates) if dates else date.min, max(order[id(c)] for c in mine))
            keep = max(files, key=rank)
            kept = next(c for c in copies if c.raw.get("source_file", "") == keep)
            kept_date = rank(keep)[0]
            for line in copies:
                if line.raw.get("source_file", "") == keep:
                    continue
                excluded.add(id(line))
                if all(line.money.get(k) == kept.money.get(k) for k in EOB_MONEY):
                    flag("DUPLICATE_EOB_LINE", line,
                         f"same claim line also loaded from {kept.ref()}; that copy is kept and this one "
                         "is excluded from matching and totals", line.money["patient_resp"])
                else:
                    mine = line.eob_date
                    if kept_date != date.min and mine and kept_date > mine:
                        basis = f"kept by later eob_date ({kept_date.isoformat()} vs {mine.isoformat()})"
                    elif kept_date != date.min and not mine:
                        basis = (f"kept because only that copy has an eob_date ({kept_date.isoformat()}); "
                                 "confirm it is the current one")
                    else:
                        basis = ("no eob_date tells them apart, so the copy loaded last was kept; "
                                 "confirm which is current")
                    flag("REVISED_EOB_LINE", line,
                         f"a different version of this claim line is in {kept.ref()} (patient_resp "
                         f"{kept.money['patient_resp']} there vs {line.money['patient_resp']} here); "
                         f"{basis}. This copy is excluded from matching and totals",
                         line.money["patient_resp"])
            copies = [c for c in copies if c.raw.get("source_file", "") == keep]
        for repeat in copies[1:]:
            # Same document: could be two genuine units of the same service. Keep it, ask a human.
            flag("REPEATED_EOB_LINE", repeat,
                 f"identical line also at {copies[0].ref()} in the same document; confirm two units, "
                 "otherwise remove the extra row", repeat.money["patient_resp"])

    active_eob: list[Line] = []
    seen_service: dict[tuple, Line] = {}
    for line in eob:
        if id(line) in excluded:
            continue
        code = cpt_base(line.raw.get("cpt", ""))
        service = match_key(line) + (code, line.money["billed"])
        claim = norm_text(line.raw.get("claim_id", ""))
        prior = seen_service.get(service)
        if prior is not None and norm_text(prior.raw.get("claim_id", "")) != claim:
            other = prior.raw.get("claim_id") or "?"
            if code:
                flag("DUPLICATE_CLAIM", line,
                     f"same service already processed on claim {other} ({prior.ref()}); "
                     "this claim is excluded from matching and totals", line.money["patient_resp"])
                excluded_as[claim] = f"it was loaded and excluded as DUPLICATE_CLAIM of {other} ({line.ref()})"
                continue
            # Without a procedure code, two genuine same-day, same-price services look identical.
            flag("POSSIBLE_DUPLICATE_CLAIM", line,
                 f"same date, provider, and billed amount as claim {other} ({prior.ref()}) and no CPT "
                 "code to tell them apart; both are kept", line.money["patient_resp"])
        seen_service.setdefault(service, line)
        active_eob.append(line)

    # A correction that changes billed or CPT isn't recognised as a revision above. Make sure a
    # claim spread across several documents is at least visible.
    claim_files: dict[str, list[Line]] = defaultdict(list)
    for line in active_eob:
        claim = norm_text(line.raw.get("claim_id", ""))
        if claim:
            claim_files[claim].append(line)
    for lines in claim_files.values():
        files = list(dict.fromkeys(l.raw.get("source_file", "") for l in lines))
        if len(files) > 1:
            flag("CLAIM_IN_MULTIPLE_DOCUMENTS", lines[0],
                 f"claim {lines[0].raw.get('claim_id')} has active lines in {len(files)} documents "
                 f"({', '.join(files)}); if one is a correction, replace the original rows", None)

    # ---- Statements: keep only the latest statement per account.
    latest: dict[str, date] = {}
    for line in bills:
        if line.statement_date and line.statement_date > latest.get(line.raw["bill_id"], date.min):
            latest[line.raw["bill_id"]] = line.statement_date
    active_bills: list[Line] = []
    older_reported: set[tuple[str, date]] = set()
    for line in bills:
        if line.statement_date != latest.get(line.raw["bill_id"]):
            key = (line.raw["bill_id"], line.statement_date)
            if key not in older_reported:
                older_reported.add(key)
                flag("OLDER_STATEMENT", line,
                     f"statement {line.raw['statement_date']} superseded by "
                     f"{latest[line.raw['bill_id']].isoformat()} for account {line.raw['bill_id']}; ignored")
            continue
        active_bills.append(line)

    seen_bill: dict[tuple, Line] = {}
    for line in active_bills:
        key = (line.raw["bill_id"],) + match_key(line) + (
            cpt_base(line.raw.get("cpt", "")), line.money["billed"], line.money["amount_due"])
        if key in seen_bill:
            flag("DUPLICATE_CHARGE", line,
                 f"identical line already on this statement ({seen_bill[key].ref()})",
                 line.money["amount_due"])
        else:
            seen_bill[key] = line

    # ---- Resolve candidates for each bill line.
    by_claim: dict[str, list[Line]] = defaultdict(list)
    by_key: dict[tuple, list[Line]] = defaultdict(list)
    for line in active_eob:
        if line.raw.get("claim_id"):
            by_claim[norm_text(line.raw["claim_id"])].append(line)
        by_key[match_key(line)].append(line)

    groups: dict[tuple, list[Line]] = {}
    group_candidates: dict[tuple, list[Line]] = {}
    group_method: dict[tuple, str] = {}
    for bill in active_bills:
        claim = norm_text(bill.raw.get("claim_id", ""))
        candidates: list[Line] = []
        method = "claim_id"
        if claim:
            candidates = [c for c in by_claim.get(claim, []) if cpt_compatible(bill, c)]
            # A claim can span several dates (therapy, inpatient); prefer lines from this date,
            # unless the bill line is a summary of the whole claim (only the full set agrees).
            same_day = [c for c in candidates if c.service_date == bill.service_date]
            if same_day and len(same_day) < len(candidates):
                due = bill.money["amount_due"]
                day_owed = sum((c.money["patient_resp"] for c in same_day), ZERO)
                all_owed = sum((c.money["patient_resp"] for c in candidates), ZERO)
                if not (abs(due - day_owed) > tolerance and abs(due - all_owed) <= tolerance):
                    candidates = same_day
            if not by_claim.get(claim):
                why = excluded_as.get(claim) or "no loaded EOB has it"
                flag("CLAIM_ID_NOT_ON_EOB", bill,
                     f"statement cites claim {bill.raw['claim_id']} but {why}",
                     bill.money["amount_due"])
        if not candidates:
            method = "date_provider_patient"
            candidates = [c for c in by_key.get(match_key(bill), []) if cpt_compatible(bill, c)]
            if bill.money["billed"] and len(candidates) > 1:
                exact = [c for c in candidates if abs(c.money["billed"] - bill.money["billed"]) <= tolerance]
                candidates = exact or candidates
        if candidates and claim and by_claim.get(claim) and method != "claim_id":
            flag("CLAIM_ID_MISMATCH", bill,
                 f"statement cites claim {bill.raw['claim_id']} but this line matched claim "
                 f"{';'.join(sorted({c.raw.get('claim_id') or '?' for c in candidates}))} by date and provider",
                 bill.money["amount_due"])
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
        # Bill lines that resolve to the same EOB lines are compared together, so a statement
        # with one row per procedure reconciles against a claim whose EOB rows lack codes.
        key = (bill.raw["bill_id"], tuple(sorted(id(c) for c in candidates)))
        groups.setdefault(key, []).append(bill)
        group_candidates[key] = candidates
        group_method[key] = method

    # EOB lines claimed by more than one group cannot be split safely.
    usage: dict[int, int] = defaultdict(int)
    for key in groups:
        for eob_id in key[1]:
            usage[eob_id] += 1

    matches: list[dict[str, str]] = []
    for key, members in groups.items():
        candidates = group_candidates[key]
        due = sum((b.money["amount_due"] for b in members), ZERO)
        owed = sum((c.money["patient_resp"] for c in candidates), ZERO)
        diff = due - owed
        first = members[0]
        bill_refs = " | ".join(b.ref() for b in members)
        eob_refs = " | ".join(c.ref() for c in candidates)
        if any(usage[i] > 1 for i in key[1]):
            status = "REVIEW_AMBIGUOUS"
            flag("AMBIGUOUS_MATCH", first,
                 "these EOB lines also match other statement lines; compare by hand",
                 None, source=bill_refs)
        elif diff > tolerance:
            status = "OVERBILLED"
            flag("OVERBILLED", first, f"statement asks {due} but EOB patient responsibility is {owed}",
                 diff, source=bill_refs)
        elif diff < -tolerance:
            status = "BILL_BELOW_EOB"
            flag("BILL_BELOW_EOB", first,
                 f"statement asks {due}, EOB says {owed}; may reflect a payment already made",
                 -diff, source=bill_refs)
        elif len(members) > 1 and any(b.money["amount_due"] <= ZERO for b in members):
            # Totals agree, but a zero/credit line can hide an overcharge on another line.
            status = "REVIEW_PARTIAL"
            flag("PARTIAL_PAYMENT_IN_GROUP", first,
                 "totals agree, but a zero or credit line in this group could be offsetting an "
                 "overcharge on another line; check line by line", None, source=bill_refs)
        else:
            status = "OK"
        billed = sum((b.money["billed"] for b in members), ZERO)
        if status != "REVIEW_AMBIGUOUS" and all(b.money["billed"] for b in members):
            eob_billed = sum((c.money["billed"] for c in candidates), ZERO)
            if abs(eob_billed - billed) > tolerance:
                flag("BILLED_MISMATCH", first,
                     f"provider billed {billed} on statement but {eob_billed} on EOB",
                     abs(eob_billed - billed), source=bill_refs)
        matches.append({
            "bill_id": first.raw["bill_id"],
            "statement_date": first.raw["statement_date"],
            "service_date": first.raw["service_date"],
            "provider": first.raw["provider"],
            "patient": first.raw["patient"],
            "bill_lines": str(len(members)),
            "eob_lines": str(len(candidates)),
            "amount_due": f"{due:.2f}",
            "eob_patient_resp": f"{owed:.2f}",
            "difference": f"{diff:.2f}",
            "status": status,
            "method": group_method[key],
            "claim_ids": ";".join(sorted({c.raw.get("claim_id", "") for c in candidates})),
            "bill_source": bill_refs,
            "eob_sources": eob_refs,
        })

    # ---- Accumulators from de-duplicated EOB lines, keyed by normalized patient.
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: ZERO))
    labels: dict[str, str] = {}
    for line in active_eob:
        labels.setdefault(line.patient_key, line.raw["patient"])
        t = totals[line.patient_key]
        for col in EOB_MONEY:
            t[col] += line.money.get(col, ZERO)
    accumulators = {}
    for patient_key, t in totals.items():
        patient = labels[patient_key]
        acc = {k: f"{v:.2f}" for k, v in t.items()}
        if args.deductible is not None:
            ded = args.deductible
            acc["deductible_remaining"] = f"{max(ded - t['deductible_applied'], ZERO):.2f}"
            if t["deductible_applied"] > ded + tolerance:
                exceptions.append({"code": "DEDUCTIBLE_EXCEEDED", "kind": "summary",
                                   "patient": patient, "amount": f"{t['deductible_applied'] - ded:.2f}",
                                   "detail": f"deductible applied {t['deductible_applied']} exceeds plan deductible {ded}"})
        if args.oop_max is not None:
            oop = args.oop_max
            acc["oop_remaining"] = f"{max(oop - t['patient_resp'], ZERO):.2f}"
            if t["patient_resp"] > oop + tolerance:
                exceptions.append({"code": "OOP_MAX_EXCEEDED", "kind": "summary",
                                   "patient": patient, "amount": f"{t['patient_resp'] - oop:.2f}",
                                   "detail": f"patient responsibility {t['patient_resp']} exceeds out-of-pocket max {oop}"})
        accumulators[patient] = acc

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    match_cols = ["bill_id", "statement_date", "service_date", "provider", "patient", "bill_lines",
                  "eob_lines", "amount_due", "eob_patient_resp", "difference", "status", "method",
                  "claim_ids", "bill_source", "eob_sources"]
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
        "eob_lines_used": len(active_eob),
        "bill_lines": len(bills),
        "bill_lines_used": len(active_bills),
        "match_groups": len(matches),
        "exceptions": dict(sorted(counts.items())),
        "accumulators": accumulators,
        "warnings": [e for e in eob_errs + bill_errs if is_warning(e)],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"RECONCILE=PASS groups={len(matches)} exceptions={len(exceptions)} out={out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check input CSVs")
    v.add_argument("--eob", type=Path, required=True)
    v.add_argument("--bills", type=Path)
    v.add_argument("--aliases", type=Path)
    v.add_argument("--tolerance", type=money_arg, default=Decimal("1.00"))
    v.set_defaults(func=cmd_validate)
    r = sub.add_parser("run", help="reconcile bills against EOB lines")
    r.add_argument("--eob", type=Path, required=True)
    r.add_argument("--bills", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--as-of", type=date_arg, help="report date, YYYY-MM-DD (default: today)")
    r.add_argument("--no-eob-days", type=int, default=45)
    r.add_argument("--tolerance", type=money_arg, default=Decimal("1.00"))
    r.add_argument("--aliases", type=Path)
    r.add_argument("--deductible", type=money_arg)
    r.add_argument("--oop-max", type=money_arg)
    r.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "no_eob_days", 0) < 0:
        print("ERROR --no-eob-days must be 0 or more", file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except InputError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
