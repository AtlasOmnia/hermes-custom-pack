---
name: medical-bill-reconciliation
description: Use when reconciling medical bills against insurer EOBs.
version: 1.0.0
author: AtlasOmnia
license: MIT
platforms:
  - linux
  - macos
  - windows
metadata:
  hermes:
    tags:
      - healthcare
      - billing
      - insurance
      - eob
      - pdf
      - reconciliation
      - personal-finance
    related_skills:
      - ocr-and-documents
      - pdf
---
# Medical Bill Reconciliation

## Overview

Check provider bills against the insurer's Explanation of Benefits (EOB), track deductible and out-of-pocket totals, and produce a short exceptions list with draft inquiries a human sends.

The work is split into stages that never share access:

1. **Collect.** Per-portal collectors download PDFs into an inbox folder. Nothing else.
2. **Extract.** `scripts/eob_extract.py` dumps PDF text and tables; the agent maps them into fixed CSV rows, each keeping its source file and page.
3. **Validate.** `scripts/reconcile.py validate` checks columns, dates, money, and EOB arithmetic.
4. **Reconcile.** `scripts/reconcile.py run` matches bills to EOB lines and writes `matches.csv`, `exceptions.csv`, `summary.json`.
5. **Review.** The agent summarizes exceptions by dollar amount and drafts inquiries. A human decides and sends.

The scripts are offline and deterministic. The reconciler is stdlib-only; the extractor needs `pdfplumber`. Pair it with a local model if documents must not leave the machine.

## When to Use

- Matching medical statements to EOBs, finding overbilling, duplicate charges, or bills with no EOB.
- Turning a pile of EOB PDFs into a spreadsheet with traceable source pages.
- Tracking deductible and out-of-pocket progress from EOBs.
- Setting up a monthly unattended billing check.

Don't use for: filing appeals or calling insurers on someone's behalf, paying bills, interpreting coverage or medical necessity, or anything requiring the agent to log in to a main email inbox.

## Quick Start

```bash
SKILL=~/.hermes/skills/productivity/medical-bill-reconciliation
mkdir -p ~/medical-billing/{inbox/eob,inbox/bills,processed,extracted,data,runs}
cp $SKILL/templates/eob_lines.csv $SKILL/templates/bill_lines.csv $SKILL/templates/providers.csv ~/medical-billing/data/
cd ~/medical-billing

python3 $SKILL/scripts/eob_extract.py inbox/eob/*.pdf inbox/bills/*.pdf --out extracted/
# agent maps extracted/*.json into data/eob_lines.csv and data/bill_lines.csv
python3 $SKILL/scripts/reconcile.py validate --eob data/eob_lines.csv --bills data/bill_lines.csv --aliases data/providers.csv
python3 $SKILL/scripts/reconcile.py run --eob data/eob_lines.csv --bills data/bill_lines.csv \
  --aliases data/providers.csv --deductible 3000 --oop-max 8000 --out runs/$(date +%F)
```

Replace the deductible and out-of-pocket numbers with the plan's actual limits.

## Mapping Rules (the agent's part)

Read each `extracted/<file>.json` and write rows that follow the template headers exactly.

- One row per service line. Copy numbers as printed; leave unknown fields blank rather than computing them.
- Always fill `source_file` and `source_page`. Every number in the report must trace back to a page.
- Dates as `YYYY-MM-DD`. Use one consistent label per patient.
- EOB columns: `claim_id, service_date, provider, patient, cpt, billed, allowed, plan_paid, patient_resp, deductible_applied, coinsurance, copay, eob_date`. `patient_resp` is the total the member owes for that line.
- Bill columns: `bill_id` (provider account or statement number), `statement_date`, `service_date`, `provider`, `patient`, `cpt`, `billed`, `amount_due`, `claim_id` if printed.
- Load only the latest statement per provider account; older statements repeat the same charges.
- Pages with `needs_ocr: true` are scans. Run `ocrmypdf` on the file, extract again, and only then map.
- When validation fails, reread the source page. Never adjust a number just to make a check pass.

## Human Gates

- Logins with SMS or app MFA, CAPTCHAs, and new-device prompts are handled by a person. Collectors stop and report; they do not retry.
- No message, payment, appeal, or account change happens without the person approving the exact text.
- Do not paste real documents, member IDs, or account numbers into public issues, chats, or logs.

## Common Pitfalls

1. **One agent with every login.** Keep collectors isolated per portal and keep the reconciler away from portals. A broken login should never touch the data.
2. **Matching on amount alone.** Different visits often share a price. Match on claim number, or patient + date + provider, and use amount only to break ties.
3. **Provider name drift.** "Bayside Ortho" and "Bayside Orthopedic Specialists PA" are the same practice. Add an `alias,canonical` row to `providers.csv` instead of editing source rows.
4. **Counting repeated statements.** Monthly statements re-list old charges. Loading them all creates false duplicates.
5. **Treating extraction errors as billing errors.** Most `EOB_MATH` hits are misread columns. Confirm against the page before drafting anything.
6. **Mixing plan years.** Accumulators reset each plan year. Run one year at a time.
7. **Trusting summed accumulators over the insurer.** Totals cover only the EOBs you loaded. Compare with the insurer's accumulator page before claiming an overpayment.

## Verification Checklist

- [ ] `reconcile.py validate` prints `VALIDATION=PASS`.
- [ ] Every row has `source_file` and `source_page`; a spot check of five rows matches the PDFs.
- [ ] `reconcile.py run` prints `RECONCILE=PASS` and the run folder has `matches.csv`, `exceptions.csv`, `summary.json`.
- [ ] Each exception in the report cites the bill and EOB pages it came from.
- [ ] Drafted inquiries contain only numbers present in the cited documents and were not sent by the agent.
- [ ] `python3 -m unittest discover -s tests` passes after any script change.

## Support Files

- `scripts/eob_extract.py`: offline PDF text and table dump with OCR detection.
- `scripts/reconcile.py`: `validate` and `run` subcommands.
- `templates/eob_lines.csv`: EOB row header.
- `templates/bill_lines.csv`: bill row header.
- `templates/providers.csv`: provider alias header.
- `templates/provider-inquiry.md`: draft inquiry for a human to send.
- `references/workflow.md`: load when setting up collectors, MFA handling, folder layout, or a monthly cron.
- `references/exception-codes.md`: load when explaining exceptions or tuning matching.
- `tests/test_reconcile.py`: synthetic-data tests for validation and reconciliation.
- `tests/test_eob_extract.py`: extractor test against a generated PDF (skips when pdfplumber is absent).
