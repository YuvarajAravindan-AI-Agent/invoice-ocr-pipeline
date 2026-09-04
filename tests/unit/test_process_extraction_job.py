from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.application.ports import ExtractionJobMessage
from app.application.use_cases.process_extraction_job import ProcessExtractionJobUseCase
from app.domain.entities import Invoice, InvoiceStatus
from app.domain.extraction import ExtractionResult
from tests.unit.fakes import (
    FakeExtractionJudge,
    FakeExtractionQueue,
    FakeInvoiceRepository,
    FakeObjectStore,
    FakeOcrExtractor,
)


def _make_pending_invoice(invoices: FakeInvoiceRepository, object_store: FakeObjectStore):
    invoice_id = uuid4()
    key = f"invoices/{invoice_id}/invoice.pdf"
    object_store.put(key, b"%PDF-fake", "application/pdf")
    invoice = Invoice(
        id=invoice_id,
        status=InvoiceStatus.PENDING,
        source_file_key=key,
        uploaded_at=datetime.now(timezone.utc),
    )
    invoices.save(invoice)
    return invoice


def test_no_job_available_returns_false():
    use_case = ProcessExtractionJobUseCase(
        FakeObjectStore(),
        FakeInvoiceRepository(),
        FakeExtractionQueue(),
        FakeOcrExtractor(),
        FakeExtractionJudge(),
    )
    assert use_case.execute() is False


def test_successful_extraction_marks_invoice_extracted_and_acks():
    object_store = FakeObjectStore()
    invoices = FakeInvoiceRepository()
    queue = FakeExtractionQueue()
    invoice = _make_pending_invoice(invoices, object_store)
    queue.enqueue(invoice.id)

    extractor = FakeOcrExtractor(
        result=ExtractionResult(
            vendor_name="Acme Corp",
            invoice_number="INV-001",
            invoice_date_iso="2026-09-01T00:00:00+00:00",
            currency="INR",
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            total=Decimal("118.00"),
            confidence_score=0.95,
            line_items=[],
        )
    )
    use_case = ProcessExtractionJobUseCase(
        object_store, invoices, queue, extractor, FakeExtractionJudge()
    )

    assert use_case.execute() is True

    updated = invoices.get(invoice.id)
    assert updated.status == InvoiceStatus.EXTRACTED
    assert updated.validation_issues == []
    assert len(queue.acked) == 1
    assert len(queue.nacked) == 0


def test_low_confidence_extraction_marks_needs_review():
    object_store = FakeObjectStore()
    invoices = FakeInvoiceRepository()
    queue = FakeExtractionQueue()
    invoice = _make_pending_invoice(invoices, object_store)
    queue.enqueue(invoice.id)

    extractor = FakeOcrExtractor(
        result=ExtractionResult(
            vendor_name="Acme Corp",
            invoice_number="INV-001",
            invoice_date_iso=None,
            currency="INR",
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            total=Decimal("118.00"),
            confidence_score=0.4,
            line_items=[],
        )
    )
    use_case = ProcessExtractionJobUseCase(
        object_store, invoices, queue, extractor, FakeExtractionJudge()
    )

    use_case.execute()

    updated = invoices.get(invoice.id)
    assert updated.status == InvoiceStatus.NEEDS_REVIEW
    assert updated.validation_issues != []


def test_extractor_failure_marks_invoice_failed_and_nacks():
    object_store = FakeObjectStore()
    invoices = FakeInvoiceRepository()
    queue = FakeExtractionQueue()
    invoice = _make_pending_invoice(invoices, object_store)
    queue.enqueue(invoice.id)

    extractor = FakeOcrExtractor(error=RuntimeError("model unavailable"))
    use_case = ProcessExtractionJobUseCase(
        object_store, invoices, queue, extractor, FakeExtractionJudge()
    )

    assert use_case.execute() is True

    updated = invoices.get(invoice.id)
    assert updated.status == InvoiceStatus.FAILED
    assert updated.error_message == "model unavailable"
    assert len(queue.nacked) == 1
    assert len(queue.acked) == 0


def test_execute_with_explicit_message_skips_queue_receive():
    """Covers the push-delivery path (Catalyst's worker HTTP handler) —
    see app/adapters/catalyst/job_queue.py, whose receive() isn't
    implementable, so the message must come in as an argument instead."""
    object_store = FakeObjectStore()
    invoices = FakeInvoiceRepository()
    queue = FakeExtractionQueue()  # left empty on purpose — nothing enqueued
    invoice = _make_pending_invoice(invoices, object_store)

    extractor = FakeOcrExtractor(
        result=ExtractionResult(
            vendor_name="Acme Corp",
            invoice_number="INV-001",
            invoice_date_iso=None,
            currency="INR",
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            total=Decimal("118.00"),
            confidence_score=0.95,
            line_items=[],
        )
    )
    use_case = ProcessExtractionJobUseCase(
        object_store, invoices, queue, extractor, FakeExtractionJudge()
    )

    message = ExtractionJobMessage(invoice_id=invoice.id, receipt_handle="pushed-directly")
    assert use_case.execute(message=message) is True

    updated = invoices.get(invoice.id)
    assert updated.status == InvoiceStatus.EXTRACTED
    assert len(queue.acked) == 1  # ack() is still called, just never receive()


def test_judge_can_flag_extraction_that_passed_deterministic_checks():
    """The agentic step is the actual decision-maker, not a rubber stamp
    on top of validate_extraction() — a clean deterministic pass (high
    confidence, all fields present, arithmetic reconciles) can still be
    flagged if the judge decides to flag it (e.g. because the raw OCR
    text contradicts the parsed fields in a way no fixed rule checks
    for)."""
    object_store = FakeObjectStore()
    invoices = FakeInvoiceRepository()
    queue = FakeExtractionQueue()
    invoice = _make_pending_invoice(invoices, object_store)
    queue.enqueue(invoice.id)

    extractor = FakeOcrExtractor(
        result=ExtractionResult(
            vendor_name="Acme Corp",
            invoice_number="INV-001",
            invoice_date_iso=None,
            currency="INR",
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            total=Decimal("118.00"),
            confidence_score=0.95,
            line_items=[],
            raw_text="This looks like a menu, not an invoice.",
        )
    )
    judge = FakeExtractionJudge(
        accept=False,
        reasoning="Raw OCR text reads like a restaurant menu, not an invoice — likely misclassified document.",
        issues=["raw text inconsistent with invoice"],
    )
    use_case = ProcessExtractionJobUseCase(object_store, invoices, queue, extractor, judge)

    use_case.execute()

    updated = invoices.get(invoice.id)
    assert updated.status == InvoiceStatus.NEEDS_REVIEW
    assert "raw text inconsistent with invoice" in updated.validation_issues
    assert "menu" in updated.review_reasoning
    assert len(judge.calls) == 1
    # the judge is called with the deterministic issues as context — here, empty,
    # since this extraction passes every fixed rule on its own
    assert judge.calls[0][1] == []


def test_judge_failure_falls_back_to_deterministic_validation():
    """A down/rate-limited LLM shouldn't fail the whole job — it should
    degrade to the pre-agentic rule-based behavior."""
    object_store = FakeObjectStore()
    invoices = FakeInvoiceRepository()
    queue = FakeExtractionQueue()
    invoice = _make_pending_invoice(invoices, object_store)
    queue.enqueue(invoice.id)

    extractor = FakeOcrExtractor(
        result=ExtractionResult(
            vendor_name="Acme Corp",
            invoice_number="INV-001",
            invoice_date_iso=None,
            currency="INR",
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            total=Decimal("118.00"),
            confidence_score=0.95,
            line_items=[],
        )
    )
    judge = FakeExtractionJudge(error=RuntimeError("rate limited"))
    use_case = ProcessExtractionJobUseCase(object_store, invoices, queue, extractor, judge)

    use_case.execute()

    updated = invoices.get(invoice.id)
    # no deterministic issues on this clean extraction -> falls back to EXTRACTED
    assert updated.status == InvoiceStatus.EXTRACTED
    assert "rate limited" in updated.review_reasoning
