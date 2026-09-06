"""API service entrypoint. Thin — wires adapters to use cases and
exposes them over HTTP; no business logic lives here (see
app/domain and app/application).

Adapters requiring the Catalyst SDK are built per-request, not at
import time — see get_catalyst_app() below and
app/adapters/catalyst/object_store.py's module docstring for why.
"""

from __future__ import annotations

import os
from uuid import UUID

import uvicorn
import zcatalyst_sdk
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder

from app.adapters.catalyst.invoice_repository import CatalystDataStoreInvoiceRepository
from app.adapters.catalyst.job_queue import CatalystJobQueue
from app.adapters.catalyst.object_store import CatalystStratusObjectStore
from app.adapters.catalyst.secret_provider import CatalystEnvSecretProvider
from app.application.use_cases.get_invoice_status import GetInvoiceStatusUseCase
from app.application.use_cases.submit_invoice import SubmitInvoiceCommand, SubmitInvoiceUseCase

app = FastAPI(title="invoice-ocr-pipeline-api")

_secrets = CatalystEnvSecretProvider()


def get_catalyst_app(request: Request):
    # Per Zoho's own Flask example (docs.catalyst.zoho.com/en/serverless/
    # help/appsail/help-guides/python/flask/), initialize() takes the
    # request object and must be called per request, not once at import
    # time. UNCONFIRMED: that example passes a Flask (WSGI) request;
    # this passes a Starlette/FastAPI (ASGI) Request instead — if this
    # crashes, that mismatch is the first thing to check. The
    # documented-safe fallback is switching this service to Flask.
    return zcatalyst_sdk.initialize(req=request)


def get_submit_invoice(catalyst_app=Depends(get_catalyst_app)) -> SubmitInvoiceUseCase:
    object_store = CatalystStratusObjectStore(catalyst_app)
    invoice_repository = CatalystDataStoreInvoiceRepository(catalyst_app)
    extraction_queue = CatalystJobQueue(catalyst_app)
    return SubmitInvoiceUseCase(object_store, invoice_repository, extraction_queue)


def get_invoice_status_use_case(catalyst_app=Depends(get_catalyst_app)) -> GetInvoiceStatusUseCase:
    invoice_repository = CatalystDataStoreInvoiceRepository(catalyst_app)
    return GetInvoiceStatusUseCase(invoice_repository)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/invoices", status_code=202)
async def submit_invoice(
    file: UploadFile, use_case: SubmitInvoiceUseCase = Depends(get_submit_invoice)
) -> dict:
    file_bytes = await file.read()
    invoice_id = use_case.execute(
        SubmitInvoiceCommand(
            file_bytes=file_bytes,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "invoice",
        )
    )
    return {"invoice_id": str(invoice_id)}


@app.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: UUID,
    use_case: GetInvoiceStatusUseCase = Depends(get_invoice_status_use_case),
) -> dict:
    invoice = use_case.execute(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    return jsonable_encoder(invoice)


if __name__ == "__main__":
    # Mirrors Zoho's own Flask example exactly: read the listen port
    # from X_ZOHO_CATALYST_LISTEN_PORT at runtime rather than hardcoding
    # it in the startup command. If Catalyst assigns a dynamic port via
    # this env var, a hardcoded `--port N` CLI flag would silently
    # mismatch it — which is the leading suspect for why this service
    # fails to start with a generic "check the startup command or port"
    # error despite the app running correctly locally.
    listen_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=listen_port)
