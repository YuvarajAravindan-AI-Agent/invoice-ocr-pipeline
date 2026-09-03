"""Placeholder API entrypoint — health check only.

Once app/domain and app/application exist, this should import and wire
up the invoice-upload/extraction-status use cases instead of defining
logic inline; this file should stay a thin adapter, per docs/architecture.md.
"""

from fastapi import FastAPI

app = FastAPI(title="invoice-ocr-pipeline-api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
