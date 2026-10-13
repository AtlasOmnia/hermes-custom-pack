from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import eob_extract  # noqa: E402

try:
    import pdfplumber  # noqa: F401
    HAVE_PDFPLUMBER = True
except ImportError:
    HAVE_PDFPLUMBER = False


def make_pdf(path: Path, page_texts: list[str | None]) -> None:
    """Write a minimal valid PDF. None produces a page with no text (simulated scan)."""
    objects: list[bytes] = []
    kids = []
    font_id = 3
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")  # pages placeholder
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for text in page_texts:
        content = b""
        if text is not None:
            lines = []
            y = 740
            for line in text.splitlines():
                safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                lines.append(f"BT /F1 11 Tf 72 {y} Td ({safe}) Tj ET")
                y -= 16
            content = "\n".join(lines).encode()
        objects.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
        content_id = len(objects)
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
            b"/Resources << /Font << /F1 %d 0 R >> >> >>" % (content_id, font_id)
        )
        kids.append(len(objects))
    objects[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (
        b" ".join(b"%d 0 R" % k for k in kids), len(kids))
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))


@unittest.skipUnless(HAVE_PDFPLUMBER, "pdfplumber not installed")
class ExtractTests(unittest.TestCase):
    def test_extracts_text_and_flags_scanned_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            pdf = tmpdir / "sample_eob.pdf"
            make_pdf(pdf, ["Claim C100  Date of service 01/10/2026\nAllowed 120.00  You owe 40.00", None])
            out_dir = tmpdir / "out"
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = eob_extract.main([str(pdf), "--out", str(out_dir)])
            self.assertEqual(code, 0, buf.getvalue())
            self.assertIn("EXTRACT=PASS", buf.getvalue())
            data = json.loads((out_dir / "sample_eob.json").read_text())
            self.assertEqual(data["source_file"], "sample_eob.pdf")
            self.assertEqual(data["page_count"], 2)
            self.assertIn("C100", data["pages"][0]["text"])
            self.assertIn("40.00", data["pages"][0]["text"])
            self.assertFalse(data["pages"][0]["needs_ocr"])
            self.assertTrue(data["pages"][1]["needs_ocr"])
            self.assertEqual(data["pages_needing_ocr"], [2])
            self.assertEqual(len(data["sha256"]), 64)


class ExtractCliTests(unittest.TestCase):
    def test_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            err, out = io.StringIO(), io.StringIO()
            with redirect_stderr(err), redirect_stdout(out):
                code = eob_extract.main([str(Path(tmp) / "nope.pdf"), "--out", tmp])
            self.assertEqual(code, 1)
            self.assertIn("missing file", err.getvalue())
            self.assertIn("EXTRACT=FAIL", out.getvalue())


if __name__ == "__main__":
    unittest.main()
