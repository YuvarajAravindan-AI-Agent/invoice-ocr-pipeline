from sqlmodel import SQLModel, Field, create_engine, Session, select
from fastapi import FastAPI, HTTPException, Request
from uuid import uuid4
from datetime import datetime

app = FastAPI(title="invoice-repo")

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
    SQLModel.metadata.create_all(engine)

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
