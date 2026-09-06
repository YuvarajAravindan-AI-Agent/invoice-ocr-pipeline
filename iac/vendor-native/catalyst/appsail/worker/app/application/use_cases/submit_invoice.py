from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.ports import ExtractionQueue, InvoiceRepository, ObjectStore
from app.domain.entities import Invoice, InvoiceStatus


@dataclass
class SubmitInvoiceCommand:
    file_bytes: bytes
    content_type: str
    filename: str


class SubmitInvoiceUseCase:
    """Called from the API service: stores the uploaded file, creates the
    invoice record, and enqueues it for the worker to extract."""

    def __init__(
        self,
        object_store: ObjectStore,
        invoice_repository: InvoiceRepository,
        extraction_queue: ExtractionQueue,
    ) -> None:
        self._object_store = object_store
        self._invoices = invoice_repository
        self._queue = extraction_queue

    def execute(self, command: SubmitInvoiceCommand) -> UUID:
        invoice_id = uuid4()
        source_file_key = f"invoices/{invoice_id}/{command.filename}"

        self._object_store.put(source_file_key, command.file_bytes, command.content_type)

        invoice = Invoice(
            id=invoice_id,
            status=InvoiceStatus.PENDING,
            source_file_key=source_file_key,
            uploaded_at=datetime.now(timezone.utc),
        )
        self._invoices.save(invoice)
        self._queue.enqueue(invoice_id)

        return invoice_id
