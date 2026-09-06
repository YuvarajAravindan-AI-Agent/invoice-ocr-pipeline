"""InvoiceRepository implemented against Catalyst Data Store.

Replaces the external-Postgres approach (see git history and
../postgres/README.md for why that was tried first and abandoned):
confirmed against a live deploy that Catalyst AppSail's outbound
network rejects both raw Postgres (5432) and — even fronted by an
HTTPS reverse proxy on another box — general outbound HTTPS to a
non-Catalyst host. Data Store is a Catalyst-internal call through the
same SDK instance already used for Stratus/Zia, so there's no egress
question at all. This is a deliberate Tier 3 (proprietary) choice —
see docs/provider-matrix.md — the opposite of the portability
`app/adapters/postgres/` was written for.

Requires a table named `invoices` to exist, with these columns (Data
Store table/column creation is console-only, no CLI/SDK path exists —
see iac/vendor-native/catalyst/README.md's "One-time setup"):

    invoice_id         VarChar (255)
    status             VarChar (255)
    source_file_key    Text
    uploaded_at        DateTime
    vendor_name        VarChar (255)
    invoice_number     VarChar (255)
    invoice_date       DateTime
    currency           VarChar (255)
    subtotal           VarChar (255)   -- decimal-as-string; Data Store
    tax                VarChar (255)   -- has no arbitrary-precision
    total              VarChar (255)   -- decimal type (Data Store docs,
                                        -- checked 2026-09-06)
    confidence_score   Double
    line_items         Text            -- JSON-encoded list
    validation_issues  Text            -- JSON-encoded list
    error_message      Text
    review_reasoning   Text

UNCONFIRMED (no live Data Store table to test against yet — verify
against the real SDK before trusting this beyond a smoke test):
- ZCQL's `execute_query()` result row shape. Assumed here to be
  `[{"invoices": {"ROWID": ..., <columns>}}, ...]` (table name as the
  outer key), matching every other Zoho product's ZCQL-style response —
  if this raises a KeyError, that nesting assumption is the first
  thing to check.
- Whether numeric/decimal columns come back from `get_row()` /
  `execute_query()` as native Python types or as strings. Handled
  defensively below (`str()` before `Decimal()`, explicit `float()`),
  which is safe either way.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from app.domain.entities import Invoice, InvoiceStatus, LineItem

_TABLE = "invoices"


def _line_items_to_json(line_items: list[LineItem]) -> str:
    return json.dumps([asdict(item) for item in line_items], default=str)


def _line_items_from_json(raw: str | None) -> list[LineItem]:
    if not raw:
        return []
    items = json.loads(raw)
    return [
        LineItem(
            description=item["description"],
            quantity=Decimal(str(item["quantity"])),
            unit_price=Decimal(str(item["unit_price"])),
            amount=Decimal(str(item["amount"])),
        )
        for item in items
    ]


def _decimal_or_none(value) -> Decimal | None:
    return Decimal(str(value)) if value not in (None, "") else None


def _row_to_invoice(row: dict) -> Invoice:
    return Invoice(
        id=UUID(row["invoice_id"]),
        status=InvoiceStatus(row["status"]),
        source_file_key=row["source_file_key"],
        uploaded_at=row["uploaded_at"],
        vendor_name=row.get("vendor_name") or None,
        invoice_number=row.get("invoice_number") or None,
        invoice_date=row.get("invoice_date") or None,
        currency=row.get("currency") or None,
        subtotal=_decimal_or_none(row.get("subtotal")),
        tax=_decimal_or_none(row.get("tax")),
        total=_decimal_or_none(row.get("total")),
        confidence_score=float(row["confidence_score"]) if row.get("confidence_score") not in (None, "") else None,
        line_items=_line_items_from_json(row.get("line_items")),
        validation_issues=json.loads(row["validation_issues"]) if row.get("validation_issues") else [],
        error_message=row.get("error_message") or None,
        review_reasoning=row.get("review_reasoning") or None,
    )


class CatalystDataStoreInvoiceRepository:
    def __init__(self, catalyst_app) -> None:
        self._table = catalyst_app.datastore().table(_TABLE)
        self._zcql = catalyst_app.zcql()

    def save(self, invoice: Invoice) -> None:
        self._table.insert_row(self._row(invoice))

    def get(self, invoice_id: UUID) -> Invoice | None:
        rowid = self._find_rowid(invoice_id)
        if rowid is None:
            return None
        row = self._table.get_row(rowid)
        return _row_to_invoice(row)

    def update(self, invoice: Invoice) -> None:
        rowid = self._find_rowid(invoice.id)
        if rowid is None:
            raise LookupError(f"invoice {invoice.id} not found for update")
        data = self._row(invoice)
        data["ROWID"] = rowid
        self._table.update_row(data)

    def _find_rowid(self, invoice_id: UUID) -> str | None:
        # String-interpolated into ZCQL rather than parameterized — safe
        # only because invoice_id is always either our own uuid4() or a
        # value FastAPI already validated as a well-formed UUID via the
        # `invoice_id: UUID` path-param type before it reaches here.
        # Never do this with a raw user-text field (vendor_name etc.) —
        # those go through insert_row/update_row's dict form instead.
        query = f"SELECT ROWID FROM {_TABLE} WHERE invoice_id = '{invoice_id}'"
        rows = self._zcql.execute_query(query)
        if not rows:
            return None
        return rows[0][_TABLE]["ROWID"]

    @staticmethod
    def _row(invoice: Invoice) -> dict:
        return {
            "invoice_id": str(invoice.id),
            "status": invoice.status.value,
            "source_file_key": invoice.source_file_key,
            "uploaded_at": invoice.uploaded_at.isoformat(),
            "vendor_name": invoice.vendor_name,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "currency": invoice.currency,
            "subtotal": str(invoice.subtotal) if invoice.subtotal is not None else None,
            "tax": str(invoice.tax) if invoice.tax is not None else None,
            "total": str(invoice.total) if invoice.total is not None else None,
            "confidence_score": invoice.confidence_score,
            "line_items": _line_items_to_json(invoice.line_items),
            "validation_issues": json.dumps(invoice.validation_issues),
            "error_message": invoice.error_message,
            "review_reasoning": invoice.review_reasoning,
        }
