"""Worker service entrypoint.

Catalyst Job Scheduling delivers jobs by POSTing directly to this
service (push, not pull) — see app/adapters/catalyst/job_queue.py for
why. This handler is the actual "receive" point: it builds an
ExtractionJobMessage from the request body and calls
ProcessExtractionJobUseCase.execute(message=...) directly, rather than
having the use case call queue.receive() itself.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.adapters.catalyst.job_queue import CatalystJobQueue
from app.adapters.catalyst.object_store import CatalystStratusObjectStore
from app.adapters.catalyst.ocr_extractor import CatalystZiaOcrExtractor
from app.adapters.catalyst.secret_provider import CatalystEnvSecretProvider
from app.adapters.postgres.invoice_repository import PostgresInvoiceRepository
from app.application.ports import ExtractionJobMessage
from app.application.use_cases.process_extraction_job import ProcessExtractionJobUseCase

app = FastAPI(title="invoice-ocr-pipeline-worker")

_secrets = CatalystEnvSecretProvider()
_object_store = CatalystStratusObjectStore()
_invoice_repository = PostgresInvoiceRepository(_secrets.get("DATABASE_URL"))
_extraction_queue = CatalystJobQueue()
_ocr_extractor = CatalystZiaOcrExtractor()

_process_job = ProcessExtractionJobUseCase(
    _object_store, _invoice_repository, _extraction_queue, _ocr_extractor
)


class ProcessJobRequest(BaseModel):
    invoice_id: UUID


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/process")
def process(request: ProcessJobRequest) -> dict:
    message = ExtractionJobMessage(invoice_id=request.invoice_id, receipt_handle="catalyst-job")
    try:
        handled = _process_job.execute(message=message)
    except Exception as exc:  # noqa: BLE001 — genuinely unexpected failure, not a normal extraction failure (those are caught inside the use case); surface as 500 so Catalyst's limited job_config retry can apply
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not handled:
        raise HTTPException(status_code=400, detail="no invoice found for this job")

    return {"status": "ok"}
