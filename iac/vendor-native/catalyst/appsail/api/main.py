"""API service entrypoint. Thin — wires adapters to use cases and
exposes them over HTTP; no business logic lives here (see
app/domain and app/application).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder

from app.adapters.catalyst.job_queue import CatalystJobQueue
from app.adapters.catalyst.object_store import CatalystStratusObjectStore
from app.adapters.catalyst.secret_provider import CatalystEnvSecretProvider
from app.adapters.postgres.invoice_repository import PostgresInvoiceRepository
from app.application.use_cases.get_invoice_status import GetInvoiceStatusUseCase
from app.application.use_cases.submit_invoice import SubmitInvoiceCommand, SubmitInvoiceUseCase

app = FastAPI(title="invoice-ocr-pipeline-api")

_secrets = CatalystEnvSecretProvider()
_object_store = CatalystStratusObjectStore()
_invoice_repository = PostgresInvoiceRepository(_secrets.get("DATABASE_URL"))
_extraction_queue = CatalystJobQueue()

_submit_invoice = SubmitInvoiceUseCase(_object_store, _invoice_repository, _extraction_queue)
_get_invoice_status = GetInvoiceStatusUseCase(_invoice_repository)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/invoices", status_code=202)
async def submit_invoice(file: UploadFile) -> dict:
    file_bytes = await file.read()
    invoice_id = _submit_invoice.execute(
        SubmitInvoiceCommand(
            file_bytes=file_bytes,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "invoice",
        )
    )
    return {"invoice_id": str(invoice_id)}


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: UUID) -> dict:
    invoice = _get_invoice_status.execute(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    return jsonable_encoder(invoice)
