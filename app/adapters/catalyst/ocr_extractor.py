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
    -> {'confidence': <int>, 'text': <str>}                 (image input)
    -> {'text': <str>}                                      (PDF input,
       confirmed against a live response — no 'confidence' key at all
       when the PDF has a real text layer; this is direct text
       extraction, not visual OCR)
Source: https://docs.catalyst.zoho.com/en/sdk/python/v1/zia/ocr/

NOTE: `app.zia()` as the accessor is inferred from the same pattern as
app.stratus()/app.job_scheduling() (see object_store.py/job_queue.py)
but wasn't directly confirmed — verify against the SDK before relying
on this.

Takes an already-initialized CatalystApp — see object_store.py's module
docstring for why this isn't constructed with zcatalyst_sdk.initialize()
internally.
"""

from __future__ import annotations

import io

from app.adapters.catalyst._invoice_text_parser import parse_invoice_text
from app.domain.extraction import ExtractionResult


_EXTENSION_BY_CONTENT_TYPE = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "application/pdf": "pdf",
}


class _NamedBytesIO(io.BytesIO):
    """A plain io.BytesIO has no .name — io.BufferedReader.name is
    read-only and derived from its wrapped raw stream, so a bare
    BufferedReader(BytesIO(...)) has none either. The underlying
    `requests` library (used internally by the SDK) relies on that
    attribute to set the multipart filename/content-type; without it,
    the upload has no filename and Zia's backend can't detect the image
    format, causing a generic CatalystZiaError({'code': 'ML_ERROR',
    'message': 'Unable to process the request'}) — confirmed by testing
    identical requests with and without a name set. Subclassing BytesIO
    (rather than assigning .name on the built-in class directly, which
    fails with AttributeError: not writable) is what makes the
    attribute settable.
    """


class CatalystZiaOcrExtractor:
    def __init__(self, catalyst_app) -> None:
        self._zia = catalyst_app.zia()

    def extract(self, file_bytes: bytes, content_type: str) -> ExtractionResult:
        # The SDK's own _is_valid_file_type check does a strict
        # isinstance(file, io.BufferedReader) — a plain io.BytesIO fails
        # it with CatalystZiaError("Invalid-Argument", "File must be a
        # instance of BufferReader"), confirmed via a real error caught
        # in production. io.BufferedReader normally wraps a RawIOBase,
        # but wrapping a BytesIO works fine in practice (it only needs
        # readinto()) and satisfies the isinstance check.
        extension = _EXTENSION_BY_CONTENT_TYPE.get(content_type, "bin")
        named_stream = _NamedBytesIO(file_bytes)
        named_stream.name = f"invoice.{extension}"
        response = self._zia.extract_optical_characters(
            io.BufferedReader(named_stream),
            # SDK's ICatalystOCROptions TypedDict key is model_type
            # (snake_case), not modelType — confirmed by reading the
            # installed SDK source directly, not docs (which showed
            # modelType). The wrong key was likely silently ignored by
            # the API, causing generic ML_ERROR/"Unable to process the
            # request" failures instead of running OCR.
            {"language": "eng", "model_type": "OCR"},
        )
        text = response["text"]
        # For a PDF with a real text layer, Zia's response has only
        # 'text' — no 'confidence' key at all. Confirmed against a live
        # response: {'text': '<the exact, correctly extracted invoice
        # text>'} — this is direct text-layer extraction, not visual
        # OCR, so 1.0 is an honest value here, not a guess papering over
        # a missing field. Images still return {'confidence': <0-100>,
        # 'text': <str>} per the module docstring's grounded SDK call.
        confidence = response.get("confidence", 100) / 100.0

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
            raw_text=text,
        )
