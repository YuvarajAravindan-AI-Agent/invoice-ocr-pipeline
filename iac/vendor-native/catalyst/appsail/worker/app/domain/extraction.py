"""The shape an OCR/extraction result must take, regardless of which
model or provider produced it. This is the seam referenced in
docs/provider-matrix.md's open decision — whatever implements
application.ports.OcrExtractor must return this shape, whether that's
Catalyst QuickML, a self-hosted model, or a third-party API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.entities import LineItem


@dataclass
class ExtractionResult:
    vendor_name: str | None
    invoice_number: str | None
    invoice_date_iso: str | None
    currency: str | None
    subtotal: Decimal | None
    tax: Decimal | None
    total: Decimal | None
    confidence_score: float
    line_items: list[LineItem] = field(default_factory=list)
    # Raw OCR text, kept alongside the parsed fields so an ExtractionJudge
    # can reason about discrepancies between what the OCR actually saw and
    # what the (regex-based, low-accuracy) parser pulled out of it.
    raw_text: str = ""
