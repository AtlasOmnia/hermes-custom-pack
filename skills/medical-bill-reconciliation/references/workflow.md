# Workflow: collect, extract, reconcile, review

Load this when setting up the full monthly routine. The SKILL.md core covers a single run.

## Folder layout

```
~/medical-billing/
  inbox/            # collectors drop PDFs here, nothing else writes here
    eob/
    bills/
  processed/        # PDFs moved here after their rows are written and validated
  extracted/        # eob_extract.py JSON dumps
  data/
    eob_lines.csv
    bill_lines.csv
    providers.csv   # alias,canonical
  runs/
    YYYY-MM-DD/     # matches.csv, exceptions.csv, summary.json, drafts/
```

Keep the folder outside any cloud-synced directory if the agent's model is local-only. Do not commit it to Git.

## Stage 1: collectors (one per portal)

- One collector per insurer or provider portal. Its only job is: log in, open the documents or claims page, download anything new, save to `inbox/eob/` or `inbox/bills/` with the name `<source>_<document-date>_<document-id>.pdf`.
- Give each collector its own Hermes profile or isolated browser profile so a credential for one portal is never visible to another. Store passwords in a vault or password manager the browser fills; never in prompts, skills, or CSVs.
- MFA by email: forward only the verification emails to a dedicated agent mailbox with a narrow filter (sender plus subject). The agent never gets your main inbox.
- MFA by SMS or authenticator app, CAPTCHAs, and new-device prompts stay human. The collector stops and notifies you; it does not retry in a loop.
- Collectors never message the insurer or provider, never pay, and never change account settings.
- Billing emails: a filter that forwards provider statement emails (or saves their PDF attachments) to the same agent mailbox works for practices without a portal.

## Stage 2: extract

```bash
python3 scripts/eob_extract.py inbox/eob/*.pdf inbox/bills/*.pdf --out extracted/
```

For each JSON dump, the agent appends rows to `data/eob_lines.csv` or `data/bill_lines.csv`:

- One row per service line, not per claim, when the document lists lines.
- `source_file` is the PDF name; `source_page` is the page number from the dump.
- Copy numbers exactly as printed. Do not compute a missing field; leave it blank.
- If `needs_ocr` is true, run `ocrmypdf` on that PDF and extract again before mapping. If OCR text is still unreadable, log the file as an exception for manual entry.
- Dates as YYYY-MM-DD. Patient as a consistent first name or member label.
- For statements: load only the most recent statement per provider account; older statements for the same account repeat the same charges.

Then:

```bash
python3 scripts/reconcile.py validate --eob data/eob_lines.csv --bills data/bill_lines.csv --aliases data/providers.csv
```

Fix every ERROR by rereading the source page, not by editing numbers until the check passes. EOB_MATH errors that are really on the printed EOB (rare, but it happens) can be kept; note them for the review.

Move the PDFs to `processed/` only after validation passes.

## Stage 3: reconcile

```bash
python3 scripts/reconcile.py run \
  --eob data/eob_lines.csv --bills data/bill_lines.csv \
  --aliases data/providers.csv --deductible 3000 --oop-max 8000 \
  --out runs/$(date +%F)
```

`--deductible` and `--oop-max` are the individual in-network plan limits for the plan year. Run one plan year at a time (filter or split the CSVs by service date) so accumulators reset correctly.

## Stage 4: human review

The agent writes a short report from `summary.json` and `exceptions.csv`, ordered by dollar amount:

1. OVERBILLED and DUPLICATE_* first; these are the usual money.
2. NO_EOB older than the threshold: the claim may never have been filed, or was filed to the wrong plan.
3. OOP_MAX_EXCEEDED / DEDUCTIBLE_EXCEEDED: compare with the insurer's own accumulator page before acting.
4. BILL_BELOW_EOB: usually a payment already made; confirm, no action.

For items worth pursuing, the agent fills `templates/provider-inquiry.md` into `runs/<date>/drafts/`. You read, edit, and send. Phone calls and appeals stay with you.

## Scheduling with Hermes cron

Once a month of real documents has gone through cleanly by hand, schedule it. Example prompt for a monthly cron job:

> Run the medical-bill-reconciliation workflow for ~/medical-billing: extract new PDFs in inbox/, append rows with source_file and source_page, run validate and fix only by rereading source pages, run reconcile for the current plan year, and send me the exception summary sorted by amount with draft inquiries for anything over $25. Do not contact any provider or insurer.

Collectors can run on their own schedule a day earlier. If a collector hits a human-only MFA step, the run proceeds with whatever is already in the inbox and the summary says which portal was skipped.
