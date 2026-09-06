"""Ports the domain/use-cases depend on. Every provider (Catalyst, AWS,
Azure, GCP, Alibaba) implements these in app/adapters/<provider>/ — no
port here may import a cloud SDK. See ../../docs/architecture.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.entities import Invoice
from app.domain.extraction import ExtractionResult
from app.domain.judgment import ExtractionJudgment


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def url_for(self, key: str) -> str: ...


class InvoiceRepository(Protocol):
    def save(self, invoice: Invoice) -> None: ...

    def get(self, invoice_id: UUID) -> Invoice | None: ...

    def update(self, invoice: Invoice) -> None: ...


@dataclass(frozen=True)
class ExtractionJobMessage:
    invoice_id: UUID
    receipt_handle: str  # opaque handle for ack/nack — e.g. an SQS receipt handle


class ExtractionQueue(Protocol):
    """Matches blueprint/platform.yaml's `queue` capability
    (invoice-extraction-jobs, dead_letter: true) — see the open decision
    in docs/provider-matrix.md before implementing this for Catalyst.
    """

    def enqueue(self, invoice_id: UUID) -> None: ...

    def receive(self) -> ExtractionJobMessage | None:
        """Returns None if no job is available. Pull-based so the worker
        controls its own concurrency."""
        ...

    def ack(self, message: ExtractionJobMessage) -> None: ...

    def nack(self, message: ExtractionJobMessage) -> None:
        """Return the job to the queue for retry, or to the DLQ once
        retry limits are exhausted — adapter's responsibility."""
        ...


class OcrExtractor(Protocol):
    """The seam for whichever OCR/extraction implementation is chosen —
    Catalyst QuickML, a self-hosted model, or a third-party API. See the
    open decision in docs/provider-matrix.md."""

    def extract(self, file_bytes: bytes, content_type: str) -> ExtractionResult: ...


class SecretProvider(Protocol):
    def get(self, name: str) -> str: ...


class ExtractionJudge(Protocol):
    """The one genuinely agentic seam in this pipeline: everything else
    (OCR, regex field parsing, deterministic validation.py checks) is
    fixed logic. This is where an LLM actually reasons about whether an
    extraction is trustworthy — does the vendor_name look like a real
    company or OCR noise, does subtotal + tax reconcile with total, does
    anything in the raw OCR text contradict the parsed fields — and
    decides accept vs. flag, instead of a hardcoded confidence
    threshold. See app/adapters/anthropic/extraction_judge.py."""

    def judge(self, result: ExtractionResult, deterministic_issues: list[str]) -> ExtractionJudgment: ...
