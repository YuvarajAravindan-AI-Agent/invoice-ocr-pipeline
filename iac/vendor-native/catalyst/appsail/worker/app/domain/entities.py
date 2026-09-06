"""Core entities. No cloud SDK imports here — see ../../docs/architecture.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


class InvoiceStatus(str, Enum):
    PENDING = "pending"  # uploaded, queued for extraction
    PROCESSING = "processing"  # worker has picked up the job
    EXTRACTED = "extracted"  # extraction succeeded
    NEEDS_REVIEW = "needs_review"  # extraction succeeded but validation flagged it
    FAILED = "failed"  # extraction failed after retries


@dataclass(frozen=True)
class LineItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


@dataclass
class Invoice:
    id: UUID
    status: InvoiceStatus
    source_file_key: str  # object storage key for the uploaded PDF/image
    uploaded_at: datetime

    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: datetime | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    confidence_score: float | None = None
    line_items: list[LineItem] = field(default_factory=list)
    validation_issues: list[str] = field(default_factory=list)
    error_message: str | None = None
    # The ExtractionJudge's own explanation for its accept/flag decision —
    # kept distinct from validation_issues (deterministic rule findings)
    # so a reviewer can see the agent's reasoning, not just a checklist.
    review_reasoning: str | None = None
