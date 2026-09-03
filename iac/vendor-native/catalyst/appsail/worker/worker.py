"""Placeholder OCR worker — health check only, no extraction logic yet.

Once the queue capability decision (docs/provider-matrix.md) is made,
this should poll/consume invoice-extraction-jobs and call into
app/application use cases for the actual OCR/extraction step. Runs a
minimal HTTP health endpoint in the meantime since AppSail expects a
listening process even for background workers.
"""

import os

from fastapi import FastAPI

app = FastAPI(title="invoice-ocr-pipeline-worker")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
