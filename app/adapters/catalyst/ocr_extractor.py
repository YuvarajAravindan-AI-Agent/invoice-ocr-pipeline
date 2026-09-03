"""OcrExtractor implemented against Catalyst Zia OCR.

Resolves the open decision flagged in docs/provider-matrix.md: Zia OCR
(docs.catalyst.zoho.com, checked 2026-09-03) does raw text extraction
only — confidence + text, no structured fields, no line items — so this
adapter is Zia OCR plus the regex heuristics in _invoice_text_parser.py.
This is a Tier 3, low-accuracy MVP choice made specifically because the
initial priority is low cost on Catalyst; if extraction accuracy turns
out to matter, the better replacement is a purpose-built invoice parser
on another provider (AWS Textract Analyze Expense, Azure Form
Recognizer prebuilt-invoice, Google Document AI Invoice Parser) behind
this same OcrExtractor port — that's the whole point of the port.

Grounded SDK call:
    zia.extract_optical_characters(file, {'language': 'eng', 'modelType': 'OCR'})
    -> {'confidence': <int>, 'text': <str>}
Source: https://docs.catalyst.zoho.com/en/sdk/python/v1/zia/ocr/

NOTE: `app.zia()` as the accessor is inferred from the same pattern as
app.stratus()/app.job_scheduling() (see object_store.py/job_queue.py)
but wasn't directly confirmed — verify against the SDK before relying
on this.
"""

from __future__ import annotations

import io

import zcatalyst_sdk

from app.adapters.catalyst._invoice_text_parser import parse_invoice_text
from app.domain.extraction import ExtractionResult


class CatalystZiaOcrExtractor:
    def __init__(self) -> None:
        app = zcatalyst_sdk.initialize()
        self._zia = app.zia()

    def extract(self, file_bytes: bytes, content_type: str) -> ExtractionResult:
        response = self._zia.extract_optical_characters(
            io.BytesIO(file_bytes), {"language": "eng", "modelType": "OCR"}
        )
        text = response["text"]
        confidence = response["confidence"] / 100.0  # Zia returns 0-100, our port uses 0-1

        fields = parse_invoice_text(text)

        return ExtractionResult(
            vendor_name=fields["vendor_name"],
            invoice_number=fields["invoice_number"],
            invoice_date_iso=None,  # not parsed — see _invoice_text_parser.py limitations
            currency=None,
            subtotal=fields["subtotal"],
            tax=fields["tax"],
            total=fields["total"],
            confidence_score=confidence,
            line_items=[],  # not parsed — see _invoice_text_parser.py limitations
        )
