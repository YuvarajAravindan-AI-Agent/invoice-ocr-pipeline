"""Heuristic regex parsing of raw OCR text into invoice fields.

Zia OCR (see ocr_extractor.py) returns unstructured text only — no
field-level understanding of what it's looking at. This module exists
because Catalyst has no equivalent of AWS Textract's Analyze Expense,
Azure Form Recognizer's prebuilt-invoice model, or Google Document AI's
Invoice Parser — all of which return structured fields directly, with
materially higher accuracy than regex heuristics ever will.

This is a deliberately low-investment MVP to get the Catalyst path
working end-to-end. Treat every field this produces as low-confidence
regardless of what Zia's own OCR confidence score says — Zia's score
reflects character-recognition quality, not "did we find the right
number." Revisit if extraction accuracy matters before this ships to
real users — see docs/provider-matrix.md.

Line items are intentionally NOT parsed here — tabular layout recovery
from raw text is exactly the kind of thing purpose-built invoice
parsers do and regex doesn't.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_AMOUNT = r"[\$₹]?\s*([\d,]+\.\d{2})"

_INVOICE_NUMBER_RE = re.compile(
    r"invoice\s*(?:#|no\.?|number)?\s*:\s*(\S+)", re.IGNORECASE
)  # requires an explicit colon — without it, any "invoice <word>" phrase
   # (e.g. "invoice fields", "invoice date") false-matches as a number
_TOTAL_RE = re.compile(rf"(?<!sub)total\s*[:\-]?\s*{_AMOUNT}", re.IGNORECASE)
_SUBTOTAL_RE = re.compile(rf"sub\s*total\s*[:\-]?\s*{_AMOUNT}", re.IGNORECASE)
_TAX_RE = re.compile(rf"(?:tax|gst|vat)\s*[:\-]?\s*{_AMOUNT}", re.IGNORECASE)


def _to_decimal(match: re.Match | None) -> Decimal | None:
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None


def parse_invoice_text(text: str) -> dict:
    """Returns a dict of best-guess fields — vendor_name, invoice_number,
    subtotal, tax, total. Missing fields are None; callers (see
    validate_extraction) already handle None gracefully."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Crude heuristic: vendor name is usually the first non-empty line
    # on the document. No structural signal to do better without a real
    # layout-aware model.
    vendor_name = lines[0] if lines else None

    invoice_number_match = _INVOICE_NUMBER_RE.search(text)

    return {
        "vendor_name": vendor_name,
        "invoice_number": invoice_number_match.group(1) if invoice_number_match else None,
        "subtotal": _to_decimal(_SUBTOTAL_RE.search(text)),
        "tax": _to_decimal(_TAX_RE.search(text)),
        "total": _to_decimal(_TOTAL_RE.search(text)),
    }
