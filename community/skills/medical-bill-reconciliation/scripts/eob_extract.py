#!/usr/bin/env python3
"""Dump the text and tables of EOB or medical-bill PDFs to JSON for row mapping.

Usage:
  python3 eob_extract.py INPUT.pdf [INPUT2.pdf ...] --out extracted/

Writes one <name>.json per PDF with, per page: text, tables, and needs_ocr.
needs_ocr is true when a page has no extractable text (usually a scan); run
`ocrmypdf in.pdf out.pdf` on that file and extract again.

This script does not decide what the numbers mean. Layouts differ by insurer and
provider, so the agent maps this raw dump into templates/eob_lines.csv or
templates/bill_lines.csv and keeps source_file and source_page on every row.

Requires pdfplumber (`pip install pdfplumber`). Runs fully offline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def extract(pdf_path: Path) -> dict:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise SystemExit("ERROR pdfplumber is not installed: pip install pdfplumber")
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            try:
                tables = page.extract_tables() or []
            except Exception as exc:  # malformed table geometry should not stop the file
                tables = []
                text += f"\n[table extraction failed: {exc}]"
            pages.append({
                "page": number,
                "text": text,
                "tables": tables,
                "needs_ocr": not text.strip(),
            })
    return {
        "source_file": pdf_path.name,
        "sha256": digest,
        "page_count": len(pages),
        "pages_needing_ocr": [p["page"] for p in pages if p["needs_ocr"]],
        "pages": pages,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdfs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    for pdf in args.pdfs:
        if not pdf.is_file():
            print(f"ERROR missing file: {pdf}", file=sys.stderr)
            failures += 1
            continue
        try:
            result = extract(pdf)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"ERROR {pdf.name}: {exc}", file=sys.stderr)
            failures += 1
            continue
        target = args.out / f"{pdf.stem}.json"
        target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        ocr = result["pages_needing_ocr"]
        print(f"EXTRACTED {pdf.name} pages={result['page_count']} needs_ocr={ocr or 'none'} -> {target}")
    print(f"EXTRACT={'FAIL' if failures else 'PASS'} files={len(args.pdfs)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
