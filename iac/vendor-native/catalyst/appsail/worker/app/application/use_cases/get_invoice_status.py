from __future__ import annotations

from uuid import UUID

from app.application.ports import InvoiceRepository
from app.domain.entities import Invoice


class GetInvoiceStatusUseCase:
    """Called from the API service to poll extraction status/results."""

    def __init__(self, invoice_repository: InvoiceRepository) -> None:
        self._invoices = invoice_repository

    def execute(self, invoice_id: UUID) -> Invoice | None:
        return self._invoices.get(invoice_id)
