# Medical Bill Reconciliation for Hermes Agent

Check provider bills against your insurer's Explanation of Benefits (EOB), catch overbilling and duplicates, and track deductible and out-of-pocket totals, with every number traceable to a PDF page.

Built for an r/hermesagent Operator Lab request. It's designed to run with a local model so medical documents never leave your machine.

## How it works

1. **Collect**: one isolated collector per portal drops PDFs into `inbox/`. Logins and MFA stay out of the analysis stage.
2. **Extract**: `scripts/eob_extract.py` dumps text and tables from each PDF and flags scanned pages that need OCR.
3. **Map**: Hermes turns each dump into rows in `eob_lines.csv` and `bill_lines.csv`, keeping `source_file` and `source_page`.
4. **Validate**: `reconcile.py validate` checks columns, dates, money, and EOB arithmetic. That arithmetic check catches most extraction mistakes.
5. **Reconcile**: `reconcile.py run` writes `matches.csv`, `exceptions.csv`, and `summary.json`.
6. **Review**: Hermes summarizes exceptions by dollar amount and drafts inquiries. You decide and send.

It flags overbilling, missing EOBs, claim numbers the insurer doesn't have, duplicate claims and charges, EOBs loaded twice, ambiguous matches it refuses to guess, EOB arithmetic errors, and deductible or out-of-pocket overruns. Multi-line claims are compared as a group, so a statement with one row per procedure reconciles correctly. See `references/exception-codes.md`.

## What it includes

- `SKILL.md`: the Hermes workflow
- `scripts/eob_extract.py`: offline PDF dump (needs `pdfplumber`)
- `scripts/reconcile.py`: validation and reconciliation (Python standard library only)
- `templates/`: CSV headers, provider alias file, draft inquiry letter
- `references/workflow.md`: collectors, MFA handling, folder layout, monthly cron
- `references/exception-codes.md`: what each exception means and the usual next step
- `tests/`: synthetic-data tests

## Install

```bash
git clone https://github.com/AtlasOmnia/hermes-agent-custom-pack.git
mkdir -p ~/.hermes/skills/productivity/medical-bill-reconciliation
cp -R hermes-agent-custom-pack/community/skills/medical-bill-reconciliation/. \
  ~/.hermes/skills/productivity/medical-bill-reconciliation/
pip install pdfplumber        # for the extractor
# optional, for scanned pages: brew install ocrmypdf  (or apt install ocrmypdf)
```

Windows PowerShell:

```powershell
git clone https://github.com/AtlasOmnia/hermes-agent-custom-pack.git
$dest = Join-Path $HOME ".hermes\skills\productivity\medical-bill-reconciliation"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force ".\hermes-agent-custom-pack\community\skills\medical-bill-reconciliation\*" $dest
pip install pdfplumber
```

Start a fresh session or run `/reload-skills`, then ask Hermes something like:

> Use medical-bill-reconciliation on ~/medical-billing. Extract the new PDFs, map rows with source pages, validate, and reconcile for plan year 2026 with a $3,000 deductible and $8,000 out-of-pocket max.

## Try it without real documents

```bash
cd ~/.hermes/skills/productivity/medical-bill-reconciliation
python3 -m unittest discover -s tests -v
```

## Privacy and safety

- Keep your working folder out of Git and out of cloud sync if you want local-only processing.
- Use a separate, narrowly filtered mailbox for MFA codes and billing emails. Never give the agent your main inbox.
- The scripts never contact insurers or providers. Draft letters are for you to review and send.
- Nothing here is medical, legal, or insurance advice. When totals disagree with the insurer's own accumulator page, the insurer's page is the starting point for the conversation.

## License

MIT
