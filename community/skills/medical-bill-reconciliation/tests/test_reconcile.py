from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reconcile  # noqa: E402

EOB_HEADER = ["claim_id", "service_date", "provider", "patient", "cpt", "billed", "allowed",
              "plan_paid", "patient_resp", "deductible_applied", "coinsurance", "copay",
              "eob_date", "source_file", "source_page"]
BILL_HEADER = ["bill_id", "statement_date", "service_date", "provider", "patient", "cpt",
               "billed", "amount_due", "claim_id", "source_file", "source_page"]


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = reconcile.main(argv)
    return code, out.getvalue(), err.getvalue()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class ReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.eob = write_csv(self.dir / "eob.csv", EOB_HEADER, [
            # clean match by claim id
            ["C100", "2026-01-10", "Bayside Orthopedic Specialists PA", "Alex", "99213",
             "250.00", "120.00", "80.00", "40.00", "40.00", "0", "0", "2026-02-01", "eob1.pdf", "1"],
            # overbilled visit, matched by date/provider/patient
            ["C200", "2026-02-05", "Gulf Imaging LLC", "Alex", "73721",
             "$1,200.00", "600.00", "300.00", "300.00", "300.00", "0", "0", "2026-03-01", "eob2.pdf", "2"],
            # same service processed twice under another claim
            ["C201", "2026-02-05", "Gulf Imaging LLC", "Alex", "73721",
             "1200.00", "600.00", "300.00", "300.00", "0", "0", "0", "2026-03-03", "eob3.pdf", "1"],
        ])
        self.bills = write_csv(self.dir / "bills.csv", BILL_HEADER, [
            ["ACCT-1", "2026-02-15", "2026-01-10", "Bayside Ortho", "Alex", "99213",
             "250.00", "40.00", "C100", "bill1.pdf", "1"],
            ["IMG-9", "2026-03-10", "2026-02-05", "Gulf Imaging", "Alex", "73721",
             "1200.00", "900.00", "", "bill2.pdf", "1"],
            # no EOB, old
            ["LAB-3", "2026-01-01", "2025-12-20", "Coastal Labs", "Alex", "80053",
             "90.00", "90.00", "", "bill3.pdf", "1"],
            # no EOB, recent
            ["LAB-4", "2026-03-25", "2026-03-15", "Coastal Labs", "Alex", "85025",
             "40.00", "40.00", "", "bill4.pdf", "1"],
            # duplicated line on one statement
            ["LAB-4", "2026-03-25", "2026-03-15", "Coastal Labs", "Alex", "85025",
             "40.00", "40.00", "", "bill4.pdf", "1"],
        ])
        self.aliases = write_csv(self.dir / "providers.csv", ["alias", "canonical"], [
            ["Bayside Ortho", "Bayside Orthopedic Specialists"],
        ])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_validate_passes_clean_input(self) -> None:
        code, out, _ = run(["validate", "--eob", str(self.eob), "--bills", str(self.bills)])
        self.assertEqual(code, 0, out)
        self.assertIn("VALIDATION=PASS", out)

    def test_validate_flags_bad_money_date_and_math(self) -> None:
        bad = write_csv(self.dir / "bad.csv", EOB_HEADER, [
            ["X1", "13/45/2026", "Prov", "Alex", "", "abc", "100", "50", "10", "", "", "", "", "f.pdf", "1"],
            ["X2", "2026-01-01", "Prov", "Alex", "", "100", "100", "50", "10", "", "", "", "", "f.pdf", "2"],
        ])
        code, out, _ = run(["validate", "--eob", str(bad)])
        self.assertEqual(code, 1)
        self.assertIn("service_date", out)
        self.assertIn("billed", out)
        self.assertIn("EOB_MATH", out)
        self.assertIn("VALIDATION=FAIL", out)

    def test_missing_required_column_is_an_error(self) -> None:
        bad = write_csv(self.dir / "nocols.csv", ["claim_id", "service_date"], [["A", "2026-01-01"]])
        code, _, err = run(["validate", "--eob", str(bad)])
        self.assertEqual(code, 1)
        self.assertIn("missing required columns", err)

    def test_run_refuses_invalid_input(self) -> None:
        bad = write_csv(self.dir / "bad.csv", EOB_HEADER, [
            ["X1", "2026-01-01", "Prov", "Alex", "", "oops", "100", "50", "50", "", "", "", "", "f.pdf", "1"],
        ])
        code, _, err = run(["run", "--eob", str(bad), "--bills", str(self.bills), "--out", str(self.dir / "o")])
        self.assertEqual(code, 1)
        self.assertIn("RECONCILE=FAIL", err)
        self.assertFalse((self.dir / "o").exists())

    def test_run_produces_expected_exceptions(self) -> None:
        out_dir = self.dir / "run"
        code, out, err = run([
            "run", "--eob", str(self.eob), "--bills", str(self.bills), "--out", str(out_dir),
            "--as-of", "2026-04-01", "--aliases", str(self.aliases),
            "--deductible", "300", "--oop-max", "500",
        ])
        self.assertEqual(code, 0, err)
        self.assertIn("RECONCILE=PASS", out)
        summary = json.loads((out_dir / "summary.json").read_text())
        exc = summary["exceptions"]
        self.assertEqual(exc.get("DUPLICATE_CLAIM"), 1)
        self.assertEqual(exc.get("DUPLICATE_CHARGE"), 1)
        self.assertEqual(exc.get("NO_EOB"), 1)
        self.assertEqual(exc.get("NO_EOB_PENDING"), 2)
        self.assertEqual(exc.get("OOP_MAX_EXCEEDED"), 1)
        self.assertEqual(exc.get("DEDUCTIBLE_EXCEEDED"), 1)
        self.assertNotIn("EOB_MATH", exc)

        matches = {m["bill_id"]: m for m in read_rows(out_dir / "matches.csv")}
        self.assertEqual(matches["ACCT-1"]["status"], "OK")
        self.assertEqual(matches["ACCT-1"]["method"], "claim_id")
        # Imaging bill matches both EOB claims for that service; owed 600 vs due 900.
        self.assertEqual(matches["IMG-9"]["method"], "date_provider_patient")
        self.assertEqual(matches["IMG-9"]["eob_patient_resp"], "600.00")
        self.assertEqual(matches["IMG-9"]["status"], "OVERBILLED")

        rows = read_rows(out_dir / "exceptions.csv")
        for row in rows:
            if row["kind"] != "summary":
                self.assertTrue(row["source"].endswith(")"), row)
                self.assertIn(".pdf p", row["source"])
        acc = summary["accumulators"]["Alex"]
        self.assertEqual(acc["patient_resp"], "640.00")
        self.assertEqual(acc["oop_remaining"], "0.00")

    def test_provider_alias_required_for_unrelated_names(self) -> None:
        out_dir = self.dir / "noalias"
        code, _, err = run([
            "run", "--eob", str(self.eob), "--bills", str(self.bills), "--out", str(out_dir),
            "--as-of", "2026-04-01",
        ])
        self.assertEqual(code, 0, err)
        matches = {m["bill_id"]: m for m in read_rows(out_dir / "matches.csv")}
        # Claim id still matches even without an alias.
        self.assertIn("ACCT-1", matches)

    def test_alias_enables_match_without_claim_id(self) -> None:
        bills = write_csv(self.dir / "bills2.csv", BILL_HEADER, [
            ["ACCT-1", "2026-02-15", "2026-01-10", "Bayside Ortho", "Alex", "", "250.00", "40.00", "", "b.pdf", "1"],
        ])
        no_alias = self.dir / "a"
        run(["run", "--eob", str(self.eob), "--bills", str(bills), "--out", str(no_alias), "--as-of", "2026-02-20"])
        self.assertEqual(read_rows(no_alias / "matches.csv"), [])
        with_alias = self.dir / "b"
        run(["run", "--eob", str(self.eob), "--bills", str(bills), "--out", str(with_alias),
             "--as-of", "2026-02-20", "--aliases", str(self.aliases)])
        rows = read_rows(with_alias / "matches.csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "OK")

    def test_money_and_date_parsing(self) -> None:
        self.assertEqual(str(reconcile.parse_money("$1,234.50")), "1234.50")
        self.assertEqual(str(reconcile.parse_money("(20.00)")), "-20.00")
        self.assertEqual(str(reconcile.parse_money("")), "0")
        self.assertEqual(reconcile.parse_date("3/7/2026").isoformat(), "2026-03-07")
        with self.assertRaises(ValueError):
            reconcile.parse_money("twelve")


if __name__ == "__main__":
    unittest.main()
