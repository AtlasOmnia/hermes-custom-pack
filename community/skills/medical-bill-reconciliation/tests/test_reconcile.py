from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reconcile  # noqa: E402

EOB_HEADER = ["claim_id", "service_date", "provider", "patient", "cpt", "billed", "allowed",
              "plan_paid", "patient_resp", "deductible_applied", "coinsurance", "copay",
              "eob_date", "source_file", "source_page"]
BILL_HEADER = ["bill_id", "statement_date", "service_date", "provider", "patient", "cpt",
               "billed", "amount_due", "claim_id", "source_file", "source_page"]


def eob_row(claim, svc, provider, cpt, billed, allowed, paid, resp, ded="0", src="eob.pdf",
            page="1", patient="Alex"):
    return [claim, svc, provider, patient, cpt, billed, allowed, paid, resp, ded, "0", "0",
            "2026-03-01", src, page]


def bill_row(bill_id, stmt, svc, provider, cpt, billed, due, claim="", src="bill.pdf",
             page="1", patient="Alex"):
    return [bill_id, stmt, svc, provider, patient, cpt, billed, due, claim, src, page]


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = reconcile.main(argv)
        except SystemExit as exc:  # argparse rejects bad flags with exit code 2
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.n = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def reconcile(self, eob_rows, bill_rows, *extra, aliases=None, as_of="2026-04-01"):
        self.n += 1
        eob = write_csv(self.dir / f"eob{self.n}.csv", EOB_HEADER, eob_rows)
        bills = write_csv(self.dir / f"bills{self.n}.csv", BILL_HEADER, bill_rows)
        out = self.dir / f"out{self.n}"
        argv = ["run", "--eob", str(eob), "--bills", str(bills), "--out", str(out)]
        if as_of:
            argv += ["--as-of", as_of]
        if aliases is not None:
            alias_file = write_csv(self.dir / f"al{self.n}.csv", ["alias", "canonical"], aliases)
            argv += ["--aliases", str(alias_file)]
        code, stdout, stderr = run(argv + list(extra))
        self.assertEqual(code, 0, stderr)
        self.assertIn("RECONCILE=PASS", stdout)
        summary = json.loads((out / "summary.json").read_text())
        return summary, read_rows(out / "matches.csv"), read_rows(out / "exceptions.csv")


class EndToEnd(Base):
    def test_mixed_scenario(self) -> None:
        summary, matches, exc_rows = self.reconcile(
            [
                eob_row("C100", "2026-01-10", "Bayside Orthopedic Specialists, P.A.", "99213",
                        "250.00", "120.00", "80.00", "40.00", ded="40.00", src="eob1.pdf"),
                eob_row("C200", "2026-02-05", "Gulf Imaging LLC", "73721",
                        "$1,200.00", "600.00", "300.00", "300.00", ded="300.00", src="eob2.pdf", page="2"),
                eob_row("C201", "2026-02-05", "Gulf Imaging LLC", "73721",
                        "1200.00", "600.00", "300.00", "300.00", src="eob3.pdf"),
            ],
            [
                bill_row("ACCT-1", "2026-02-15", "2026-01-10", "Bayside Ortho", "99213", "250.00", "40.00",
                         claim="C100", src="bill1.pdf"),
                bill_row("IMG-9", "2026-03-10", "2026-02-05", "Gulf Imaging", "73721", "1200.00", "900.00",
                         src="bill2.pdf"),
                bill_row("LAB-3", "2026-01-01", "2025-12-20", "Coastal Labs", "80053", "90.00", "90.00",
                         src="bill3.pdf"),
                bill_row("LAB-4", "2026-03-25", "2026-03-15", "Coastal Labs", "85025", "40.00", "40.00",
                         src="bill4.pdf"),
                bill_row("LAB-4", "2026-03-25", "2026-03-15", "Coastal Labs", "85025", "40.00", "40.00",
                         src="bill4.pdf"),
            ],
            "--deductible", "300", "--oop-max", "300",
            aliases=[["Bayside Ortho", "Bayside Orthopedic Specialists PA"]],
        )
        self.assertEqual(summary["exceptions"], {
            "DEDUCTIBLE_EXCEEDED": 1, "DUPLICATE_CHARGE": 1, "DUPLICATE_CLAIM": 1,
            "NO_EOB": 1, "NO_EOB_PENDING": 2, "OOP_MAX_EXCEEDED": 1, "OVERBILLED": 1,
        })
        by_id = {m["bill_id"]: m for m in matches}
        self.assertEqual(by_id["ACCT-1"]["status"], "OK")
        self.assertEqual(by_id["ACCT-1"]["method"], "claim_id")
        # Duplicate claim C201 is excluded, so the imaging bill is compared with C200 only.
        self.assertEqual(by_id["IMG-9"]["claim_ids"], "C200")
        self.assertEqual(by_id["IMG-9"]["eob_patient_resp"], "300.00")
        self.assertEqual(by_id["IMG-9"]["status"], "OVERBILLED")
        self.assertEqual(by_id["IMG-9"]["difference"], "600.00")
        for row in exc_rows:
            if row["kind"] != "summary":
                self.assertRegex(row["source"], r"\.pdf p\d+ \(row \d+\)")
        acc = summary["accumulators"]["Alex"]
        self.assertEqual(acc["patient_resp"], "340.00")
        self.assertEqual(acc["deductible_applied"], "340.00")
        self.assertEqual(acc["oop_remaining"], "0.00")
        self.assertEqual(summary["eob_lines_used"], 2)


class Duplicates(Base):
    def test_bill_for_both_duplicate_claims_is_overbilled(self) -> None:
        summary, matches, _ = self.reconcile(
            [eob_row("C200", "2026-02-05", "Gulf Imaging", "73721", "1200", "600", "300", "300", src="a.pdf"),
             eob_row("C201", "2026-02-05", "Gulf Imaging", "73721", "1200", "600", "300", "300", src="b.pdf")],
            [bill_row("IMG-9", "2026-03-10", "2026-02-05", "Gulf Imaging", "73721", "1200", "600")],
        )
        self.assertEqual(summary["exceptions"], {"DUPLICATE_CLAIM": 1, "OVERBILLED": 1})
        self.assertEqual(matches[0]["difference"], "300.00")

    def test_same_claim_loaded_from_two_documents_is_excluded(self) -> None:
        row = ["C100", "2026-01-10", "Bayside Ortho", "99213", "250", "120", "80", "40"]
        summary, matches, _ = self.reconcile(
            [eob_row(*row, ded="40", src="eob.pdf"), eob_row(*row, ded="40", src="eob-corrected.pdf")],
            [bill_row("ACCT-1", "2026-02-20", "2026-01-10", "Bayside Ortho", "99213", "250", "40", claim="C100")],
        )
        self.assertEqual(summary["exceptions"], {"DUPLICATE_EOB_LINE": 1})
        self.assertEqual(matches[0]["status"], "OK")
        self.assertEqual(summary["accumulators"]["Alex"]["billed"], "250.00")
        self.assertEqual(summary["accumulators"]["Alex"]["deductible_applied"], "40.00")

    def test_identical_lines_in_one_document_are_kept_and_flagged(self) -> None:
        row = ["C100", "2026-01-10", "Clinic", "96372", "50", "30", "20", "10"]
        summary, matches, _ = self.reconcile(
            [eob_row(*row, src="eob.pdf"), eob_row(*row, src="eob.pdf")],
            [bill_row("A", "2026-02-20", "2026-01-10", "Clinic", "", "", "20", claim="C100")],
        )
        self.assertEqual(summary["exceptions"], {"REPEATED_EOB_LINE": 1})
        self.assertEqual(matches[0]["eob_patient_resp"], "20.00")
        self.assertEqual(matches[0]["status"], "OK")

    def test_older_statement_for_same_account_is_ignored(self) -> None:
        eob = [eob_row("C1", "2026-01-10", "Clinic", "99213", "100", "80", "60", "20")]
        summary, matches, _ = self.reconcile(eob, [
            bill_row("ACC", "2026-02-01", "2026-01-10", "Clinic", "99213", "100", "20", src="jan.pdf"),
            bill_row("ACC", "2026-03-01", "2026-01-10", "Clinic", "99213", "100", "20", src="feb.pdf"),
        ])
        self.assertEqual(summary["exceptions"], {"OLDER_STATEMENT": 1})
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["status"], "OK")
        self.assertIn("feb.pdf", matches[0]["bill_source"])


class MultiLineClaims(Base):
    EOB = [
        eob_row("C300", "2026-03-01", "Clinic", "", "100", "80", "60", "20"),
        eob_row("C300", "2026-03-01", "Clinic", "", "50", "40", "30", "10", page="2"),
        eob_row("C300", "2026-03-01", "Clinic", "", "30", "20", "15", "5", page="3"),
    ]

    def lines(self, dues):
        return [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", cpt, billed, due, claim="C300")
                for cpt, billed, due in zip(["99213", "36415", "80053"], ["100", "50", "30"], dues)]

    def test_correct_per_procedure_statement_is_ok(self) -> None:
        summary, matches, _ = self.reconcile(self.EOB, self.lines(["20", "10", "5"]))
        self.assertEqual(summary["exceptions"], {})
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["status"], "OK")
        self.assertEqual(matches[0]["bill_lines"], "3")
        self.assertEqual(matches[0]["eob_lines"], "3")

    def test_overcharge_on_one_line_is_caught(self) -> None:
        summary, matches, _ = self.reconcile(self.EOB, self.lines(["20", "10", "35"]))
        self.assertEqual(summary["exceptions"], {"OVERBILLED": 1})
        self.assertEqual(matches[0]["difference"], "30.00")

    def test_summary_bill_line_matches_whole_claim(self) -> None:
        summary, matches, _ = self.reconcile(
            self.EOB, [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "", "180", "35", claim="C300")])
        self.assertEqual(summary["exceptions"], {})
        self.assertEqual(matches[0]["status"], "OK")

    def test_coded_eob_lines_match_per_procedure(self) -> None:
        eob = [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20"),
               eob_row("C1", "2026-03-01", "Clinic", "36415", "50", "40", "30", "10")]
        bills = [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "99213", "100", "20", claim="C1"),
                 bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "36415", "50", "25", claim="C1")]
        summary, matches, _ = self.reconcile(eob, bills)
        self.assertEqual(len(matches), 2)
        self.assertEqual(sorted(m["status"] for m in matches), ["OK", "OVERBILLED"])
        self.assertEqual(summary["exceptions"], {"OVERBILLED": 1})

    def test_overlapping_matches_are_ambiguous_not_guessed(self) -> None:
        eob = [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20"),
               eob_row("C1", "2026-03-01", "Clinic", "36415", "50", "40", "30", "10")]
        bills = [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "", "", "30", claim="C1"),
                 bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "99213", "100", "20", claim="C1")]
        summary, matches, _ = self.reconcile(eob, bills)
        self.assertEqual({m["status"] for m in matches}, {"REVIEW_AMBIGUOUS"})
        self.assertEqual(summary["exceptions"], {"AMBIGUOUS_MATCH": 2})


class Matching(Base):
    def test_cpt_modifier_still_matches(self) -> None:
        summary, matches, _ = self.reconcile(
            [eob_row("C4", "2026-03-01", "Clinic", "99213-25", "100", "80", "60", "20")],
            [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "99213", "100", "20")])
        self.assertEqual(matches[0]["status"], "OK")
        self.assertEqual(summary["exceptions"], {})

    def test_different_cpt_does_not_match(self) -> None:
        summary, matches, _ = self.reconcile(
            [eob_row("C4", "2026-03-01", "Clinic", "99214", "100", "80", "60", "20")],
            [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "99213", "100", "20")],
            as_of="2026-06-01")
        self.assertEqual(matches, [])
        self.assertEqual(summary["exceptions"], {"NO_EOB": 1})

    def test_claim_id_with_cpt_narrowing(self) -> None:
        eob = [eob_row("C5", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20"),
               eob_row("C5", "2026-03-01", "Clinic", "36415", "50", "40", "30", "10")]
        _, matches, _ = self.reconcile(
            eob, [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "36415", "50", "10", claim="C5")])
        self.assertEqual(matches[0]["eob_patient_resp"], "10.00")
        self.assertEqual(matches[0]["status"], "OK")

    def test_unknown_claim_id_is_flagged_even_when_fallback_matches(self) -> None:
        summary, matches, _ = self.reconcile(
            [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20")],
            [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "99213", "100", "20", claim="C999")])
        self.assertEqual(summary["exceptions"], {"CLAIM_ID_NOT_ON_EOB": 1})
        self.assertEqual(matches[0]["method"], "date_provider_patient")

    def test_bill_below_eob_and_billed_mismatch(self) -> None:
        summary, matches, _ = self.reconcile(
            [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20")],
            [bill_row("ACC", "2026-03-25", "2026-03-01", "Clinic", "99213", "140", "5", claim="C1")])
        self.assertEqual(summary["exceptions"], {"BILL_BELOW_EOB": 1, "BILLED_MISMATCH": 1})
        self.assertEqual(matches[0]["status"], "BILL_BELOW_EOB")

    def test_tolerance_boundary(self) -> None:
        eob = [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20")]
        _, at, _ = self.reconcile(eob, [bill_row("A", "2026-03-25", "2026-03-01", "Clinic", "", "", "21.00", claim="C1")])
        self.assertEqual(at[0]["status"], "OK")
        _, over, _ = self.reconcile(eob, [bill_row("A", "2026-03-25", "2026-03-01", "Clinic", "", "", "21.01", claim="C1")])
        self.assertEqual(over[0]["status"], "OVERBILLED")

    def test_no_eob_days_boundary(self) -> None:
        bills = [bill_row("A", "2026-01-01", "2025-12-20", "Lab", "", "", "10")]
        s45, _, _ = self.reconcile([], bills, "--no-eob-days", "45", as_of="2026-02-15")
        self.assertEqual(s45["exceptions"], {"NO_EOB": 1})
        s44, _, _ = self.reconcile([], bills, "--no-eob-days", "45", as_of="2026-02-14")
        self.assertEqual(s44["exceptions"], {"NO_EOB_PENDING": 1})

    def test_default_as_of_is_today(self) -> None:
        class FakeDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 2, 15)

        with mock.patch.object(reconcile, "date", FakeDate):
            summary, _, _ = self.reconcile(
                [], [bill_row("A", "2026-01-01", "2025-12-20", "Lab", "", "", "10")], as_of=None)
        self.assertEqual(summary["as_of"], "2026-02-15")
        self.assertEqual(summary["exceptions"], {"NO_EOB": 1})

    def test_patient_label_case_shares_accumulator(self) -> None:
        summary, _, _ = self.reconcile(
            [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "40", "40", patient="Alex"),
             eob_row("C2", "2026-03-02", "Clinic", "99213", "100", "80", "40", "40", patient="alex")],
            [], "--oop-max", "50")
        self.assertEqual(list(summary["accumulators"]), ["Alex"])
        self.assertEqual(summary["exceptions"], {"OOP_MAX_EXCEEDED": 1})


class Providers(Base):
    def test_dotted_suffixes_normalize(self) -> None:
        def norm(name):
            return reconcile.norm_provider(name, {})
        self.assertEqual(norm("Bayside Orthopedic Specialists, P.A."), "bayside orthopedic specialists")
        self.assertEqual(norm("Bayside Orthopedic Specialists PA"), "bayside orthopedic specialists")
        self.assertEqual(norm("John Smith, M.D."), "john smith")
        self.assertEqual(norm("Gulf Imaging, L.L.C."), "gulf imaging")
        self.assertEqual(norm("St. Anne Clinic"), "st anne clinic")

    def test_alias_canonical_with_suffix_matches_plain_name(self) -> None:
        eob = [eob_row("C1", "2026-01-10", "Bayside Orthopedic Specialists", "99213", "250", "120", "80", "40")]
        bills = [bill_row("A", "2026-02-15", "2026-01-10", "Bayside Ortho", "", "250", "40")]
        _, without, _ = self.reconcile(eob, bills, as_of="2026-02-20")
        self.assertEqual(without, [])
        _, with_alias, _ = self.reconcile(
            eob, bills, aliases=[["Bayside Ortho", "Bayside Orthopedic Specialists PA"]], as_of="2026-02-20")
        self.assertEqual(with_alias[0]["status"], "OK")

    def test_malformed_alias_file_fails(self) -> None:
        eob = write_csv(self.dir / "e.csv", EOB_HEADER, [])
        bad = write_csv(self.dir / "bad_alias.csv", ["name", "canonical"], [["x", "y"]])
        code, _, err = run(["validate", "--eob", str(eob), "--aliases", str(bad)])
        self.assertEqual(code, 1)
        self.assertIn("alias,canonical", err)
        blank = write_csv(self.dir / "blank_alias.csv", ["alias", "canonical"], [["x", ""]])
        code, _, err = run(["validate", "--eob", str(eob), "--aliases", str(blank)])
        self.assertEqual(code, 1)
        self.assertIn("both required", err)


class Validation(Base):
    def test_validate_passes_clean_input(self) -> None:
        eob = write_csv(self.dir / "e.csv", EOB_HEADER,
                        [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20")])
        code, out, _ = run(["validate", "--eob", str(eob)])
        self.assertEqual(code, 0, out)
        self.assertIn("VALIDATION=PASS", out)

    def test_validate_flags_bad_money_date_math_and_empty_required(self) -> None:
        bad = write_csv(self.dir / "bad.csv", EOB_HEADER, [
            eob_row("X1", "13/45/2026", "Prov", "", "abc", "100", "50", "10"),
            eob_row("X2", "2026-01-01", "Prov", "", "100", "100", "50", "10"),
            eob_row("X3", "2026-01-01", "Prov", "", "100", "100", "50", "50", patient=""),
        ])
        code, out, _ = run(["validate", "--eob", str(bad)])
        self.assertEqual(code, 1)
        self.assertIn("service_date", out)
        self.assertIn("billed", out)
        self.assertIn("EOB_MATH", out)
        self.assertIn("empty required field patient", out)
        self.assertIn("VALIDATION=FAIL", out)

    def test_missing_required_column_is_an_error(self) -> None:
        bad = write_csv(self.dir / "nocols.csv", ["claim_id", "service_date"], [["A", "2026-01-01"]])
        code, _, err = run(["validate", "--eob", str(bad)])
        self.assertEqual(code, 1)
        self.assertIn("missing required columns", err)

    def test_unknown_column_is_a_warning_recorded_in_summary(self) -> None:
        eob = write_csv(self.dir / "e.csv", EOB_HEADER + ["notes"],
                        [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20") + ["x"]])
        bills = write_csv(self.dir / "b.csv", BILL_HEADER, [])
        code, out, _ = run(["validate", "--eob", str(eob)])
        self.assertEqual(code, 0)
        self.assertIn("WARN", out)
        code, _, _ = run(["run", "--eob", str(eob), "--bills", str(bills), "--out", str(self.dir / "o"),
                          "--as-of", "2026-04-01"])
        self.assertEqual(code, 0)
        summary = json.loads((self.dir / "o" / "summary.json").read_text())
        self.assertTrue(any("notes" in w for w in summary["warnings"]))

    def test_run_refuses_invalid_input(self) -> None:
        bad = write_csv(self.dir / "bad.csv", EOB_HEADER,
                        [eob_row("X1", "2026-01-01", "Prov", "", "oops", "100", "50", "50")])
        bills = write_csv(self.dir / "b.csv", BILL_HEADER, [])
        code, _, err = run(["run", "--eob", str(bad), "--bills", str(bills), "--out", str(self.dir / "o")])
        self.assertEqual(code, 1)
        self.assertIn("RECONCILE=FAIL", err)
        self.assertFalse((self.dir / "o").exists())

    def test_bad_numeric_flags_are_rejected(self) -> None:
        eob = write_csv(self.dir / "e.csv", EOB_HEADER, [])
        bills = write_csv(self.dir / "b.csv", BILL_HEADER, [])
        base = ["run", "--eob", str(eob), "--bills", str(bills), "--out", str(self.dir / "o")]
        for flag, value in [("--tolerance", "abc"), ("--tolerance", "-5"), ("--deductible", "lots"),
                            ("--oop-max", "-1"), ("--as-of", "2026-13-01")]:
            code, _, err = run(base + [flag, value])
            self.assertEqual(code, 2, f"{flag} {value}")
            self.assertIn(flag, err)
        code, _, _ = run(base + ["--no-eob-days", "-1"])
        self.assertEqual(code, 2)
        self.assertFalse((self.dir / "o").exists())

    def test_money_and_date_parsing(self) -> None:
        self.assertEqual(str(reconcile.parse_money("$1,234.50")), "1234.50")
        self.assertEqual(str(reconcile.parse_money("(20.00)")), "-20.00")
        self.assertEqual(str(reconcile.parse_money("")), "0")
        self.assertEqual(reconcile.parse_date("3/7/2026").isoformat(), "2026-03-07")
        for bad in ["2026-1-5", "03-07-2026", "3/7/26", "2026-02-30"]:
            with self.assertRaises(ValueError):
                reconcile.parse_date(bad)
        with self.assertRaises(ValueError):
            reconcile.parse_money("twelve")


class CriticRegressions(Base):
    """Scenarios from the second independent review."""

    def corrected(self, original_resp="40", corrected_resp="25", corrected_first=False):
        original = ["C100", "2026-01-10", "Clinic", "Alex", "99213", "250", "120", "80", original_resp,
                    original_resp, "0", "0", "2026-02-01", "eob.pdf", "1"]
        fixed = ["C100", "2026-01-10", "Clinic", "Alex", "99213", "250", "120",
                 str(120 - int(corrected_resp)), corrected_resp, corrected_resp, "0", "0",
                 "2026-02-20", "eob-corrected.pdf", "1"]
        return [fixed, original] if corrected_first else [original, fixed]

    def test_corrected_eob_replaces_original_and_overbill_is_caught(self) -> None:
        for corrected_first in (False, True):
            summary, matches, _ = self.reconcile(
                self.corrected(corrected_first=corrected_first),
                [bill_row("A", "2026-03-01", "2026-01-10", "Clinic", "99213", "250", "40", claim="C100")])
            self.assertEqual(summary["exceptions"], {"OVERBILLED": 1, "REVISED_EOB_LINE": 1})
            self.assertEqual(matches[0]["status"], "OVERBILLED")
            self.assertEqual(matches[0]["difference"], "15.00")
            acc = summary["accumulators"]["Alex"]
            self.assertEqual((acc["billed"], acc["patient_resp"], acc["deductible_applied"]),
                             ("250.00", "25.00", "25.00"))

    def test_partial_payment_inside_group_is_not_ok(self) -> None:
        eob = [eob_row("C300", "2026-03-01", "Clinic", "", "100", "80", "60", "20"),
               eob_row("C300", "2026-03-01", "Clinic", "", "50", "40", "30", "10")]
        bills = [bill_row("A", "2026-03-25", "2026-03-01", "Clinic", "99213", "100", "30", claim="C300"),
                 bill_row("A", "2026-03-25", "2026-03-01", "Clinic", "36415", "50", "0", claim="C300")]
        summary, matches, _ = self.reconcile(eob, bills)
        self.assertEqual(matches[0]["status"], "REVIEW_PARTIAL")
        self.assertEqual(summary["exceptions"], {"PARTIAL_PAYMENT_IN_GROUP": 1})

    def test_multi_date_claim_matches_the_bill_date(self) -> None:
        eob = [eob_row("C1", "2026-03-01", "Rehab", "97110", "100", "80", "60", "20"),
               eob_row("C1", "2026-03-03", "Rehab", "97110", "100", "80", "50", "30")]
        summary, matches, _ = self.reconcile(
            eob, [bill_row("A", "2026-03-25", "2026-03-01", "Rehab", "97110", "100", "20", claim="C1")])
        self.assertEqual(summary["exceptions"], {})
        self.assertEqual(matches[0]["status"], "OK")

    def test_same_day_claims_without_cpt_are_kept(self) -> None:
        eob = [eob_row("L1", "2026-03-01", "Lab", "", "50", "30", "20", "10"),
               eob_row("L2", "2026-03-01", "Lab", "", "50", "30", "20", "10", src="eob2.pdf")]
        summary, matches, _ = self.reconcile(
            eob, [bill_row("A", "2026-03-25", "2026-03-01", "Lab", "", "100", "20")])
        self.assertEqual(summary["exceptions"], {"POSSIBLE_DUPLICATE_CLAIM": 1})
        self.assertEqual(matches[0]["status"], "OK")
        self.assertEqual(summary["accumulators"]["Alex"]["patient_resp"], "20.00")

    def test_cited_claim_resolving_elsewhere_is_flagged(self) -> None:
        eob = [eob_row("C1", "2026-03-01", "Clinic", "99213", "100", "80", "60", "20"),
               eob_row("C2", "2026-03-01", "Clinic", "36415", "50", "40", "30", "10")]
        summary, matches, rows = self.reconcile(
            eob, [bill_row("A", "2026-03-25", "2026-03-01", "Clinic", "36415", "50", "10", claim="C1")])
        self.assertEqual(summary["exceptions"], {"CLAIM_ID_MISMATCH": 1})
        self.assertEqual(matches[0]["claim_ids"], "C2")
        self.assertIn("C2", rows[0]["detail"])

    def test_claim_excluded_as_duplicate_is_explained(self) -> None:
        eob = [eob_row("C200", "2026-02-05", "Imaging", "73721", "1200", "600", "300", "300", src="a.pdf"),
               eob_row("C201", "2026-02-05", "Imaging", "73721", "1200", "600", "300", "300", src="b.pdf")]
        _, _, rows = self.reconcile(
            eob, [bill_row("A", "2026-03-10", "2026-02-05", "Imaging", "73721", "1200", "300", claim="C201")])
        detail = next(r["detail"] for r in rows if r["code"] == "CLAIM_ID_NOT_ON_EOB")
        self.assertIn("excluded as DUPLICATE_CLAIM of C200", detail)

    def test_undated_revision_says_why_it_kept_a_copy(self) -> None:
        rows = self.corrected()
        rows[0][12] = ""  # original undated
        _, _, exc = self.reconcile(
            rows, [bill_row("A", "2026-03-01", "2026-01-10", "Clinic", "99213", "250", "25", claim="C100")])
        detail = next(r["detail"] for r in exc if r["code"] == "REVISED_EOB_LINE")
        self.assertIn("only that copy has an eob_date", detail)
        rows[1][12] = ""  # both undated
        _, _, exc = self.reconcile(
            rows, [bill_row("A", "2026-03-01", "2026-01-10", "Clinic", "99213", "250", "25", claim="C100")])
        detail = next(r["detail"] for r in exc if r["code"] == "REVISED_EOB_LINE")
        self.assertIn("confirm which is current", detail)
        self.assertNotIn("later", detail)

    def test_correction_changing_billed_is_visible(self) -> None:
        rows = self.corrected()
        rows[1][5] = "275"
        summary, _, _ = self.reconcile(
            rows, [bill_row("A", "2026-03-01", "2026-01-10", "Clinic", "99213", "275", "25", claim="C100")])
        self.assertIn("CLAIM_IN_MULTIPLE_DOCUMENTS", summary["exceptions"])

    def test_summary_line_for_multi_date_claim_uses_whole_claim(self) -> None:
        eob = [eob_row("C1", "2026-03-01", "Rehab", "97110", "100", "80", "60", "20"),
               eob_row("C1", "2026-03-03", "Rehab", "97110", "100", "80", "50", "30")]
        summary, matches, _ = self.reconcile(
            eob, [bill_row("A", "2026-03-25", "2026-03-01", "Rehab", "", "200", "50", claim="C1")])
        self.assertEqual(matches[0]["status"], "OK")
        self.assertEqual(matches[0]["eob_lines"], "2")
        self.assertEqual(summary["exceptions"], {})


if __name__ == "__main__":
    unittest.main()
