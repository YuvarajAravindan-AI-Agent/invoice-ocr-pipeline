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
