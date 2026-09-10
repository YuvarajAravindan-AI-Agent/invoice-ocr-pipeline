from fastapi.testclient import TestClient
import importlib.util
from pathlib import Path
app_path = Path('services/invoice-repo/app.py')
spec = importlib.util.spec_from_file_location('invoice_repo_app', app_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
invoice_app = mod.app
# Ensure DB tables exist (avoid relying on startup hook ordering in tests)
mod.SQLModel.metadata.create_all(mod.engine)
from app.adapters.http.invoice_repository import HttpInvoiceRepository
import requests

client = TestClient(invoice_app)

class ShimResponse:
    def __init__(self, response):
        self._r = response
        self.status_code = response.status_code
    def json(self):
        return self._r.json()
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


def path_from_url(url: str) -> str:
    # assume base like http://example or http://test
    return '/' + '/'.join(url.split('://',1)[1].split('/')[1:]) if '/' in url.split('://',1)[1] else '/' 


def test_get_against_invoice_repo(monkeypatch):
    # insert an invoice directly into the invoice-repo DB with lowercase status
    from uuid import uuid4
    from datetime import datetime
    inv = mod.Invoice(id=str(uuid4()), status='pending', source_file_key='', uploaded_at=datetime.utcnow())
    with mod.Session(mod.engine) as sess:
        sess.add(inv)
        sess.commit()
        sess.refresh(inv)
        invoice_id = inv.id

    # monkeypatch requests.get to route to the TestClient
    def fake_get(url, *args, **kwargs):
        path = url.split('://',1)[1]
        if '/' in path:
            path = '/' + path.split('/',1)[1]
        else:
            path = '/'
        resp = client.get(path)
        return ShimResponse(resp)

    monkeypatch.setattr(requests, 'get', fake_get)

    repo = HttpInvoiceRepository(base_url='http://test')
    fetched = repo.get(invoice_id)
    assert fetched is not None
    assert str(fetched.id) == invoice_id
