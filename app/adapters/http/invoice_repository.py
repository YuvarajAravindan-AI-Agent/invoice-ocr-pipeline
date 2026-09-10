from __future__ import annotations

import os
from uuid import UUID
from datetime import datetime

import requests

from app.domain.entities import Invoice, InvoiceStatus


class HttpInvoiceRepository:
    """Adapter that proxies invoice persistence to an external HTTP microservice.

    Expects environment variable `INVOICE_REPO_URL`, e.g. `http://invoice-repo:8000`.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._base = base_url or os.getenv("INVOICE_REPO_URL", "http://invoice-repo:8000")

    def save(self, invoice: Invoice) -> None:
        url = f"{self._base}/invoices"
        payload = {
            "id": str(invoice.id),
            "status": invoice.status.value,
            "source_file_key": invoice.source_file_key,
            "uploaded_at": invoice.uploaded_at.isoformat(),
            "vendor_name": invoice.vendor_name,
            "invoice_number": invoice.invoice_number,
        }
        resp = requests.post(url, json=payload)
        resp.raise_for_status()

    def get(self, invoice_id: UUID) -> Invoice | None:
        url = f"{self._base}/invoices/{invoice_id}"
        resp = requests.get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

        return Invoice(
            id=UUID(data["id"]),
            status=InvoiceStatus(data.get("status")),
            source_file_key=data.get("source_file_key"),
            uploaded_at=datetime.fromisoformat(data.get("uploaded_at")),
            vendor_name=data.get("vendor_name"),
            invoice_number=data.get("invoice_number"),
        )

    def update(self, invoice: Invoice) -> None:
        url = f"{self._base}/invoices/{invoice.id}"
        payload = {"status": invoice.status.value}
        resp = requests.patch(url, json=payload)
        resp.raise_for_status()
