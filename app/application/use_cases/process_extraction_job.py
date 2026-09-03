from __future__ import annotations

from datetime import datetime

from app.application.ports import (
    ExtractionQueue,
    InvoiceRepository,
    ObjectStore,
    OcrExtractor,
)
from app.domain.entities import InvoiceStatus
from app.domain.validation import validate_extraction


class ProcessExtractionJobUseCase:
    """Called from the worker: pulls one job off the queue, runs
    extraction, validates the result, and updates the invoice record.
    Returns False if there was no job to process, so the worker's poll
    loop can back off."""

    def __init__(
        self,
        object_store: ObjectStore,
        invoice_repository: InvoiceRepository,
        extraction_queue: ExtractionQueue,
        ocr_extractor: OcrExtractor,
    ) -> None:
        self._object_store = object_store
        self._invoices = invoice_repository
        self._queue = extraction_queue
        self._extractor = ocr_extractor

    def execute(self) -> bool:
        message = self._queue.receive()
        if message is None:
            return False

        invoice = self._invoices.get(message.invoice_id)
        if invoice is None:
            # Job references an invoice we no longer have a record for —
            # drop it rather than retrying forever.
            self._queue.ack(message)
            return True

        invoice.status = InvoiceStatus.PROCESSING
        self._invoices.update(invoice)

        try:
            file_bytes = self._object_store.get(invoice.source_file_key)
            result = self._extractor.extract(file_bytes, content_type="application/octet-stream")
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any extractor failure means retry/DLQ, not crash the worker
            invoice.status = InvoiceStatus.FAILED
            invoice.error_message = str(exc)
            self._invoices.update(invoice)
            self._queue.nack(message)
            return True

        issues = validate_extraction(result)

        invoice.vendor_name = result.vendor_name
        invoice.invoice_number = result.invoice_number
        invoice.invoice_date = (
            datetime.fromisoformat(result.invoice_date_iso) if result.invoice_date_iso else None
        )
        invoice.currency = result.currency
        invoice.subtotal = result.subtotal
        invoice.tax = result.tax
        invoice.total = result.total
        invoice.confidence_score = result.confidence_score
        invoice.line_items = result.line_items
        invoice.validation_issues = issues
        invoice.status = InvoiceStatus.NEEDS_REVIEW if issues else InvoiceStatus.EXTRACTED

        self._invoices.update(invoice)
        self._queue.ack(message)
        return True
