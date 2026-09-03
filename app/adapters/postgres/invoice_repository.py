"""InvoiceRepository implemented against plain PostgreSQL — see README.md
in this directory for why this isn't nested under a provider directory.

Uses psycopg (v3). Schema: schema.sql in this directory.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.domain.entities import Invoice, InvoiceStatus, LineItem


def _line_items_to_json(line_items: list[LineItem]) -> str:
    return json.dumps([asdict(item) for item in line_items], default=str)


def _line_items_from_json(raw: list[dict] | None) -> list[LineItem]:
    if not raw:
        return []
    return [
        LineItem(
            description=item["description"],
            quantity=Decimal(str(item["quantity"])),
            unit_price=Decimal(str(item["unit_price"])),
            amount=Decimal(str(item["amount"])),
        )
        for item in raw
    ]


def _row_to_invoice(row: dict) -> Invoice:
    return Invoice(
        id=row["id"],
        status=InvoiceStatus(row["status"]),
        source_file_key=row["source_file_key"],
        uploaded_at=row["uploaded_at"],
        vendor_name=row["vendor_name"],
        invoice_number=row["invoice_number"],
        invoice_date=row["invoice_date"],
        currency=row["currency"],
        subtotal=row["subtotal"],
        tax=row["tax"],
        total=row["total"],
        confidence_score=row["confidence_score"],
        line_items=_line_items_from_json(row["line_items"]),
        validation_issues=list(row["validation_issues"] or []),
        error_message=row["error_message"],
    )


class PostgresInvoiceRepository:
    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._connection_string, row_factory=dict_row)

    def save(self, invoice: Invoice) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO invoices (
                    id, status, source_file_key, uploaded_at,
                    vendor_name, invoice_number, invoice_date, currency,
                    subtotal, tax, total, confidence_score,
                    line_items, validation_issues, error_message
                ) VALUES (
                    %(id)s, %(status)s, %(source_file_key)s, %(uploaded_at)s,
                    %(vendor_name)s, %(invoice_number)s, %(invoice_date)s, %(currency)s,
                    %(subtotal)s, %(tax)s, %(total)s, %(confidence_score)s,
                    %(line_items)s, %(validation_issues)s, %(error_message)s
                )
                """,
                self._params(invoice),
            )

    def get(self, invoice_id: UUID) -> Invoice | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
            row = cur.fetchone()
            return _row_to_invoice(row) if row else None

    def update(self, invoice: Invoice) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE invoices SET
                    status = %(status)s,
                    vendor_name = %(vendor_name)s,
                    invoice_number = %(invoice_number)s,
                    invoice_date = %(invoice_date)s,
                    currency = %(currency)s,
                    subtotal = %(subtotal)s,
                    tax = %(tax)s,
                    total = %(total)s,
                    confidence_score = %(confidence_score)s,
                    line_items = %(line_items)s,
                    validation_issues = %(validation_issues)s,
                    error_message = %(error_message)s
                WHERE id = %(id)s
                """,
                self._params(invoice),
            )

    @staticmethod
    def _params(invoice: Invoice) -> dict:
        return {
            "id": invoice.id,
            "status": invoice.status.value,
            "source_file_key": invoice.source_file_key,
            "uploaded_at": invoice.uploaded_at,
            "vendor_name": invoice.vendor_name,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "currency": invoice.currency,
            "subtotal": invoice.subtotal,
            "tax": invoice.tax,
            "total": invoice.total,
            "confidence_score": invoice.confidence_score,
            "line_items": _line_items_to_json(invoice.line_items),
            "validation_issues": json.dumps(invoice.validation_issues),
            "error_message": invoice.error_message,
        }
