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
from datetime import datetime
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


_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _format_datetime(dt) -> str:
    # Data Store's DateTime columns expect "YYYY-MM-DD HH:MM:SS" — not
    # datetime.isoformat()'s "T" separator or microseconds. Confirmed
    # against a live CatalystAPIError (INVALID_INPUT, "Invalid input
    # value for column name") before this fix.
    return dt.strftime(_DATETIME_FORMAT)


def _parse_datetime(value: str | None):
    # get_row()/execute_query() hand back DateTime columns as this same
    # "YYYY-MM-DD HH:MM:SS" string, not a datetime object — parse it back
    # so a round-tripped Invoice (get() then update(), as
    # ProcessExtractionJobUseCase does at the PROCESSING step) has a real
    # datetime for _format_datetime() to call .strftime() on, not a
    # string. Without this, update() on an Invoice that came from get()
    # crashes the same way the pre-strftime-fix code did directly against
    # a live worker ('str' object has no attribute 'isoformat').
    return datetime.strptime(value, _DATETIME_FORMAT) if value else None


def _row_to_invoice(row: dict) -> Invoice:
    return Invoice(
        id=UUID(row["invoice_id"]),
        status=InvoiceStatus(row["status"]),
        source_file_key=row["source_file_key"],
        uploaded_at=_parse_datetime(row["uploaded_at"]),
        vendor_name=row.get("vendor_name") or None,
        invoice_number=row.get("invoice_number") or None,
        invoice_date=_parse_datetime(row.get("invoice_date")),
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
        # Data Store's insert_row rejects explicit nulls for optional
        # columns (same INVALID_INPUT error as the datetime format) —
        # omit unset fields entirely rather than sending them as None.
        row = {k: v for k, v in self._row(invoice).items() if v is not None}
        self._table.insert_row(row)

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
        data = {k: v for k, v in self._row(invoice).items() if v is not None}
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
            "uploaded_at": _format_datetime(invoice.uploaded_at),
            "vendor_name": invoice.vendor_name,
            "invoice_number": invoice.invoice_number,
            "invoice_date": _format_datetime(invoice.invoice_date) if invoice.invoice_date else None,
            "currency": invoice.currency,
            "subtotal": str(invoice.subtotal) if invoice.subtotal is not None else None,
            "tax": str(invoice.tax) if invoice.tax is not None else None,
            "total": str(invoice.total) if invoice.total is not None else None,
            "confidence_score": invoice.confidence_score,
            # Sent as None (and dropped by save()/update()'s None-filter)
            # rather than "[]" when empty — unconfirmed whether Data
            # Store's Text columns actually reject "[]", but there's no
            # downside to omitting an empty value, and get()/_row_to_invoice
            # already treats a missing column as an empty list.
            "line_items": _line_items_to_json(invoice.line_items) if invoice.line_items else None,
            "validation_issues": json.dumps(invoice.validation_issues) if invoice.validation_issues else None,
            "error_message": invoice.error_message,
            "review_reasoning": invoice.review_reasoning,
        }
