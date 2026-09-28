"""PDF document tool: extract clean text and reject unreadable/empty files."""
from __future__ import annotations

import pymupdf


class PDFExtractionError(ValueError):
    pass


def extract_pdf_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        raise PDFExtractionError("The uploaded PDF is empty.")
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            text = "\n\n".join(page.get_text("text") for page in document)
    except Exception as exc:
        raise PDFExtractionError(f"Could not read this PDF: {exc}") from exc
    clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not clean:
        raise PDFExtractionError("No selectable text was found in this PDF. Scanned PDFs need OCR before evaluation.")
    return clean
