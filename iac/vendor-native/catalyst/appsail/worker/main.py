"""Worker service entrypoint.

Catalyst Job Scheduling delivers jobs by POSTing directly to this
service (push, not pull) — see app/adapters/catalyst/job_queue.py for
why. This handler is the actual "receive" point: it builds an
ExtractionJobMessage from the request body and calls
ProcessExtractionJobUseCase.execute(message=...) directly, rather than
having the use case call queue.receive() itself.

Adapters requiring the Catalyst SDK are built per-request, not at
import time — see get_catalyst_app() below and
app/adapters/catalyst/object_store.py's module docstring for why.
"""

from __future__ import annotations

import os
from uuid import UUID

import uvicorn
import zcatalyst_sdk
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.adapters.deepseek.extraction_judge import DeepSeekExtractionJudge
from app.adapters.catalyst.invoice_repository import CatalystDataStoreInvoiceRepository
from app.adapters.catalyst.job_queue import CatalystJobQueue
from app.adapters.catalyst.object_store import CatalystStratusObjectStore
from app.adapters.catalyst.ocr_extractor import CatalystZiaOcrExtractor
from app.adapters.catalyst.secret_provider import CatalystEnvSecretProvider
from app.adapters.http.invoice_repository import HttpInvoiceRepository
from app.application.ports import ExtractionJobMessage
from app.application.use_cases.process_extraction_job import ProcessExtractionJobUseCase

app = FastAPI(title="invoice-ocr-pipeline-worker")

_secrets = CatalystEnvSecretProvider()


def get_catalyst_app(request: Request):
    # See iac/vendor-native/catalyst/appsail/api/main.py's version of
    # this function for the full explanation and the FastAPI/Flask
    # request-object caveat.
    return zcatalyst_sdk.initialize(req=request)


def get_process_job(catalyst_app=Depends(get_catalyst_app)) -> ProcessExtractionJobUseCase:
    object_store = CatalystStratusObjectStore(catalyst_app)
    use_http = os.getenv('USE_HTTP_INVOICE_REPO', 'false').lower() in ('1','true','yes')
    invoice_repo_url = os.getenv('INVOICE_REPO_URL')
    if use_http and invoice_repo_url:
        invoice_repository = HttpInvoiceRepository(base_url=invoice_repo_url)
    elif use_http and not invoice_repo_url:
        invoice_repository = HttpInvoiceRepository()
    else:
        invoice_repository = CatalystDataStoreInvoiceRepository(catalyst_app)
    extraction_queue = CatalystJobQueue(catalyst_app)
    ocr_extractor = CatalystZiaOcrExtractor(catalyst_app)
    extraction_judge = DeepSeekExtractionJudge(_secrets.get("DEEPSEEK_API_KEY"))
    return ProcessExtractionJobUseCase(
        object_store, invoice_repository, extraction_queue, ocr_extractor, extraction_judge
    )


class ProcessJobRequest(BaseModel):
    invoice_id: UUID


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/process")
def process(
    body: ProcessJobRequest, use_case: ProcessExtractionJobUseCase = Depends(get_process_job)
) -> dict:
    message = ExtractionJobMessage(invoice_id=body.invoice_id, receipt_handle="catalyst-job")
    try:
        handled = use_case.execute(message=message)
    except Exception as exc:  # noqa: BLE001 — genuinely unexpected failure, not a normal extraction failure (those are caught inside the use case); surface as 500 so Catalyst's limited job_config retry can apply
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not handled:
        raise HTTPException(status_code=400, detail="no invoice found for this job")

    return {"status": "ok"}


if __name__ == "__main__":
    # See api/main.py's version of this block for why the port is read
    # from X_ZOHO_CATALYST_LISTEN_PORT rather than hardcoded.
    listen_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=listen_port)
