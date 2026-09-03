"""In-memory fakes for app.application.ports — test doubles only, not
real adapters. Real adapters live in app/adapters/<provider>/ and are
not implemented yet.
"""

from __future__ import annotations

from collections import deque
from uuid import UUID

from app.application.ports import ExtractionJobMessage
from app.domain.entities import Invoice
from app.domain.extraction import ExtractionResult


class FakeObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def url_for(self, key: str) -> str:
        return f"fake://{key}"


class FakeInvoiceRepository:
    def __init__(self) -> None:
        self.invoices: dict[UUID, Invoice] = {}

    def save(self, invoice: Invoice) -> None:
        self.invoices[invoice.id] = invoice

    def get(self, invoice_id: UUID) -> Invoice | None:
        return self.invoices.get(invoice_id)

    def update(self, invoice: Invoice) -> None:
        self.invoices[invoice.id] = invoice


class FakeExtractionQueue:
    def __init__(self) -> None:
        self._pending: deque[ExtractionJobMessage] = deque()
        self.acked: list[ExtractionJobMessage] = []
        self.nacked: list[ExtractionJobMessage] = []

    def enqueue(self, invoice_id: UUID) -> None:
        self._pending.append(
            ExtractionJobMessage(invoice_id=invoice_id, receipt_handle=str(len(self._pending)))
        )

    def receive(self) -> ExtractionJobMessage | None:
        return self._pending.popleft() if self._pending else None

    def ack(self, message: ExtractionJobMessage) -> None:
        self.acked.append(message)

    def nack(self, message: ExtractionJobMessage) -> None:
        self.nacked.append(message)
        self._pending.append(message)  # naive retry — real adapters apply backoff/DLQ limits


class FakeOcrExtractor:
    def __init__(self, result: ExtractionResult | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error

    def extract(self, file_bytes: bytes, content_type: str) -> ExtractionResult:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result
