import json
from uuid import uuid4
from datetime import datetime

import pytest

from app.adapters.http.invoice_repository import HttpInvoiceRepository
from app.domain.entities import Invoice, InvoiceStatus


def test_save_posts(monkeypatch):
    calls = {}

    class Resp:
        status_code = 201

        def raise_for_status(self):
            return None

    def fake_post(url, json=None, **kwargs):
        calls['url'] = url
        calls['json'] = json
        return Resp()

    monkeypatch.setattr('requests.post', fake_post)

    invoice = Invoice(id=uuid4(), status=InvoiceStatus.PENDING, source_file_key='k', uploaded_at=datetime.utcnow())
    repo = HttpInvoiceRepository(base_url='http://example')
    repo.save(invoice)

    assert calls['url'] == 'http://example/invoices'
    assert calls['json']['id'] == str(invoice.id)


def test_get_returns_none_on_404(monkeypatch):
    class Resp404:
        status_code = 404

        def raise_for_status(self):
            raise Exception('not expected')

    def fake_get(url, **kwargs):
        return Resp404()

    monkeypatch.setattr('requests.get', fake_get)

    repo = HttpInvoiceRepository(base_url='http://example')
    result = repo.get(uuid4())
    assert result is None


def test_get_parses_invoice(monkeypatch):
    id = str(uuid4())
    payload = {
        'id': id,
        'status': InvoiceStatus.PENDING.value,
        'source_file_key': 'invoices/1/file.pdf',
        'uploaded_at': datetime.utcnow().isoformat(),
        'vendor_name': 'Acme',
        'invoice_number': 'INV-1',
    }

    class RespOK:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return payload

    def fake_get(url, **kwargs):
        return RespOK()

    monkeypatch.setattr('requests.get', fake_get)

    repo = HttpInvoiceRepository(base_url='http://example')
    invoice = repo.get(id)
    assert invoice is not None
    assert str(invoice.id) == id
    assert invoice.vendor_name == 'Acme'
    assert invoice.invoice_number == 'INV-1'


def test_update_calls_patch(monkeypatch):
    calls = {}

    class Resp:
        status_code = 200

        def raise_for_status(self):
            return None

    def fake_patch(url, json=None, **kwargs):
        calls['url'] = url
        calls['json'] = json
        return Resp()

    monkeypatch.setattr('requests.patch', fake_patch)

    invoice = Invoice(id=uuid4(), status=InvoiceStatus.PROCESSING, source_file_key='', uploaded_at=datetime.utcnow())
    repo = HttpInvoiceRepository(base_url='http://example')
    repo.update(invoice)
    assert calls['url'] == f'http://example/invoices/{invoice.id}'
    assert calls['json']['status'] == invoice.status.value
