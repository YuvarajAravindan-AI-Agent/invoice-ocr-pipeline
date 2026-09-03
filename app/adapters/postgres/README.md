# adapters/postgres

Not a per-cloud-provider adapter like `../catalyst/`, `../aws/`, etc. —
`InvoiceRepository` is implemented once here, against plain PostgreSQL,
because `iac/vendor-native/catalyst/README.md`'s mapping table
deliberately chose an external managed PostgreSQL over Catalyst Data
Store (NoSQL, would be Tier 3) to keep this specific capability
portable. Every provider's wiring (Catalyst, AWS, Azure, GCP, Alibaba)
uses this same class — only the connection string differs, sourced
from each provider's `SecretProvider` implementation.

Ports-and-adapters doesn't require a 1:1 mapping between adapters and
cloud providers — an adapter is scoped to whatever the actual
implementation boundary is. This is that case.

## Contents

- `schema.sql` — table definition; run manually against the target Postgres instance (no migration tool wired up yet).
- `invoice_repository.py` — `PostgresInvoiceRepository`, implemented with `psycopg` (v3).
