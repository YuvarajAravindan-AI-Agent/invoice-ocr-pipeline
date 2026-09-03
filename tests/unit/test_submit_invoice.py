from app.application.use_cases.submit_invoice import SubmitInvoiceCommand, SubmitInvoiceUseCase
from app.domain.entities import InvoiceStatus
from tests.unit.fakes import FakeExtractionQueue, FakeInvoiceRepository, FakeObjectStore


def test_submit_invoice_stores_file_creates_record_and_enqueues():
    object_store = FakeObjectStore()
    invoices = FakeInvoiceRepository()
    queue = FakeExtractionQueue()
    use_case = SubmitInvoiceUseCase(object_store, invoices, queue)

    invoice_id = use_case.execute(
        SubmitInvoiceCommand(file_bytes=b"%PDF-fake", content_type="application/pdf", filename="invoice.pdf")
    )

    invoice = invoices.get(invoice_id)
    assert invoice is not None
    assert invoice.status == InvoiceStatus.PENDING
    assert object_store.get(invoice.source_file_key) == b"%PDF-fake"

    queued_job = queue.receive()
    assert queued_job is not None
    assert queued_job.invoice_id == invoice_id
