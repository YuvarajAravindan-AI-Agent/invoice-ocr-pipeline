-- Run manually against the target PostgreSQL instance. No migration
-- tool wired up yet — if this grows past one table, adopt one instead
-- of hand-tracking schema changes.

CREATE TABLE IF NOT EXISTS invoices (
    id                 UUID PRIMARY KEY,
    status             TEXT NOT NULL,
    source_file_key    TEXT NOT NULL,
    uploaded_at        TIMESTAMPTZ NOT NULL,

    vendor_name        TEXT,
    invoice_number     TEXT,
    invoice_date       TIMESTAMPTZ,
    currency           TEXT,
    subtotal           NUMERIC(14, 2),
    tax                NUMERIC(14, 2),
    total              NUMERIC(14, 2),
    confidence_score   REAL,
    line_items         JSONB NOT NULL DEFAULT '[]',
    validation_issues  JSONB NOT NULL DEFAULT '[]',
    error_message      TEXT,
    review_reasoning   TEXT
);

CREATE INDEX IF NOT EXISTS invoices_status_idx ON invoices (status);

-- Migration for tables created before review_reasoning existed:
-- ALTER TABLE invoices ADD COLUMN IF NOT EXISTS review_reasoning TEXT;
