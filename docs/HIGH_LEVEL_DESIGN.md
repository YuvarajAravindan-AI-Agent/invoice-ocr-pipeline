# High-Level Design — LedgerLens

Purpose
- Describe modules, responsibilities, interfaces, and design rationale for maintainers and contributors.

Modules and responsibilities
- `app/application/` — use-cases implementing business workflows (SubmitInvoice, ProcessExtractionJob, GetInvoiceStatus).
- `app/domain/` — entities (Invoice), value objects, and pure domain logic.
- `app/adapters/` — provider-specific adapters implementing ports (ObjectStore, InvoiceRepository, ExtractionQueue, OcrExtractor, ExtractionJudge).
- `iap/vendor-native/` & `iac/opentofu/` — infrastructure-as-code for provider-specific deployments.

Ports & Adapters
- Define clear interfaces in `app/application/ports.py` used by use-cases. Tests use fakes in `tests/unit/fakes.py`.
- Adapters are thin: validate and translate SDK responses into domain shapes. Keep heavy logic in `app/application`.

Data model (Invoice)
- Fields: `id`, `status`, `source_file_key`, `uploaded_at`, `vendor_name`, `invoice_number`, `invoice_date`, `currency`, `subtotal`, `tax`, `total`, `confidence_score`, `line_items`, `validation_issues`, `error_message`, `review_reasoning`.

APIs
- `POST /invoices` — accepts multipart file, stores to Stratus, creates Invoice row, enqueues job. Returns `202 Accepted` and `invoice_id`.
- `GET /invoices/{id}` — returns stored Invoice data.

Configuration & Secrets
- Use layered config: `application.yaml` defaults, optional `local_application.yaml` overrides, then environment variables, then secrets manager (Catalyst secrets, GitHub Secrets for CI).
- Do not store secrets in repo; use `app/config.py` loader.

Testing strategy
- Unit tests for domain, parsers, and use-cases using fakes (existing).
- Integration tests using in-memory fakes (added); future integration will run real Docker services via `docker-compose`.
- CI: run lint, unit tests, integration tests in matrix for providers.

Scalability & Observability
- Scale worker horizontally behind Job Scheduling push-delivery.
- Add metrics around job delivery, extraction latency, and judge decisions.
- Centralized logging and error monitoring (Sentry or Cloud provider service).

