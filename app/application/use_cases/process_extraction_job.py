from __future__ import annotations

import mimetypes
from datetime import datetime

from app.application.ports import (
    ExtractionJobMessage,
    ExtractionQueue,
    InvoiceRepository,
    ObjectStore,
    OcrExtractor,
)
from app.domain.entities import InvoiceStatus
from app.domain.validation import validate_extraction


class ProcessExtractionJobUseCase:
    """Runs extraction for one job, validates the result, and updates the
    invoice record.

    Two delivery models are supported, since not every provider's queue
    works the same way (see docs/provider-matrix.md):
      - Pull-based (e.g. a worker poll loop against SQS/similar): call
        execute() with no argument — it calls extraction_queue.receive()
        itself. Returns False if there was nothing to process.
      - Push-based (e.g. Catalyst Jobs, which POST directly to the
        worker's HTTP endpoint): the adapter already has the message
        from the request body, so call execute(message=...) directly.
        extraction_queue.receive() is never called in this path.

    In both cases extraction_queue.ack()/nack() are still called at the
    end, but a push-based adapter may implement those as no-ops if the
    platform's own delivery guarantees make them meaningless — see
    app/adapters/catalyst/job_queue.py.
    """

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

    def execute(self, message: ExtractionJobMessage | None = None) -> bool:
        if message is None:
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
            # source_file_key carries the original filename (see
            # submit_invoice.py) — guessing content_type from its
            # extension rather than hardcoding application/octet-stream
            # lets extractors that need to know the format (e.g. Zia OCR
            # needing a filename it can sniff) actually get one.
            content_type = mimetypes.guess_type(invoice.source_file_key)[0] or "application/octet-stream"
            result = self._extractor.extract(file_bytes, content_type=content_type)
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
