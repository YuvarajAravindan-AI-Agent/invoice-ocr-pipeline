from sqlmodel import SQLModel, Field, create_engine, Session, select
from fastapi import FastAPI, HTTPException, Request
from uuid import uuid4
from datetime import datetime
import os

app = FastAPI(title="invoice-repo")

# Use DATABASE_URL env var when provided (Postgres), otherwise fallback to local SQLite
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, echo=False)
else:
    engine = create_engine("sqlite:///./invoices.db", echo=False, connect_args={"check_same_thread": False})

class Invoice(SQLModel, table=True):
    id: str = Field(primary_key=True)
    status: str
    source_file_key: str
    uploaded_at: datetime
    vendor_name: str | None = None
    invoice_number: str | None = None

@app.on_event("startup")
def on_startup():
    import time
    from sqlalchemy.exc import OperationalError

    # If DATABASE_URL is set we expect Alembic to manage migrations; only
    # call create_all for the SQLite fallback (local dev/test).
    if DATABASE_URL:
        # Wait for the database to be reachable before startup procedures.
        last_exc = None
        for _ in range(30):
            try:
                # simple connection check
                with engine.connect():
                    return
            except OperationalError as e:
                last_exc = e
                time.sleep(1)
        if last_exc:
            raise last_exc

    else:
        # Use create_all for SQLite fallback
        last_exc = None
        for _ in range(5):
            try:
                SQLModel.metadata.create_all(engine)
                return
            except OperationalError as e:
                last_exc = e
                time.sleep(1)
        if last_exc:
            raise last_exc


@app.post("/invoices", status_code=201)
async def create_invoice(request: Request):
    # Accept an optional invoice payload (used by HttpInvoiceRepository.save).
    data = {}
    try:
        data = await request.json()
    except Exception:
        data = {}

    invoice_id = data.get("id") or str(uuid4())
    status = data.get("status", "pending")
    source_file_key = data.get("source_file_key", "")
    uploaded_at = data.get("uploaded_at")
    if uploaded_at:
        uploaded_at = datetime.fromisoformat(uploaded_at)
    else:
        uploaded_at = datetime.utcnow()

    invoice = Invoice(id=invoice_id, status=status, source_file_key=source_file_key, uploaded_at=uploaded_at)
    with Session(engine) as sess:
        sess.add(invoice)
        sess.commit()
        sess.refresh(invoice)
    return invoice

@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    with Session(engine) as sess:
        invoice = sess.get(Invoice, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="invoice not found")
        return invoice
