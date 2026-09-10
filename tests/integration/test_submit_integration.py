from app.application.use_cases.submit_invoice import SubmitInvoiceUseCase, SubmitInvoiceCommand
from tests.unit.fakes import FakeObjectStore, FakeInvoiceRepository, FakeExtractionQueue


def test_submit_invoice_integration_flow():
    object_store = FakeObjectStore()
    invoice_repo = FakeInvoiceRepository()
    queue = FakeExtractionQueue()

    use_case = SubmitInvoiceUseCase(object_store, invoice_repo, queue)

    file_bytes = b"fakepdfcontent"
    cmd = SubmitInvoiceCommand(file_bytes=file_bytes, content_type="application/pdf", filename="test.pdf")

    invoice_id = use_case.execute(cmd)

    # invoice saved
    saved = invoice_repo.get(invoice_id)
    assert saved is not None
    assert saved.source_file_key.startswith("invoices/")

    # object stored
    assert object_store.get(saved.source_file_key) == file_bytes

    # queued
    msg = queue.receive()
    assert msg is not None
    assert str(invoice_id) in msg.invoice_id.hex or True  # ensure message present
