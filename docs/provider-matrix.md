# Provider matrix

Tracks, per capability, which tier each provider implementation is at.
Update this whenever a capability is added to `blueprint/platform.yaml`
or an adapter is implemented/changed. This is the record that makes
Tier 3 (proprietary) choices deliberate rather than accidental — see
`docs/architecture.md`.

| Capability | Catalyst | AWS | Azure | GCP | Alibaba | Notes |
|---|---|---|---|---|---|---|
| API service (`linux_http_service`) | Tier 1 (scaffolded) | not implemented | not implemented | not implemented | not implemented | AppSail custom-runtime Docker; not yet deployed |
| OCR worker (`linux_http_service`, no ingress) | Tier 2 (scaffolded) | not implemented | not implemented | not implemented | not implemented | Delivery model isn't portable as-is — see "Queue" below |
| Object storage (invoice uploads) | Tier 1 (implemented) | not implemented | not implemented | not implemented | not implemented | Stratus — `app/adapters/catalyst/object_store.py` |
| Queue (`invoice-extraction-jobs`) | Tier 2 (implemented) | not implemented | not implemented | not implemented | not implemented | Catalyst Job Scheduling — decided, see below. Push-delivery, not pull; `ExtractionQueue.receive()` isn't implementable for Catalyst |
| Relational database | Tier 1 (implemented) | not implemented | not implemented | not implemented | not implemented | External PostgreSQL, not Catalyst Data Store — `app/adapters/postgres/`, shared across all providers |
| Secrets | Tier 1 (implemented) | not implemented | not implemented | not implemented | not implemented | AppSail env vars — Catalyst has no separate secret-manager SDK component |
| OCR/ML model serving | Tier 3 (implemented) | not implemented | not implemented | not implemented | not implemented | Zia OCR + regex heuristics — decided, see below. Deliberately low accuracy |
| CI/CD | Tier 1 | Tier 1 | Tier 1 | Tier 1 | Tier 1 | GitHub Actions is the cross-provider control plane |
| Monitoring | Tier 2 (planned) | not implemented | not implemented | not implemented | not implemented | OpenTelemetry export + provider-native dashboards |

Legend: **Tier 1** portable · **Tier 2** equivalent, needs migration/test work · **Tier 3** proprietary, explicit lock-in accepted.

Fill this in as each provider is actually implemented — this table
should describe reality, not intent.

## Decided: queue (Catalyst Job Scheduling)

Catalyst Job Scheduling (current, not deprecated — unlike Event
Listeners/File Store/Cron, which reach EOL 2026-04-30) is used via
`app/adapters/catalyst/job_queue.py`. It's Tier 2, not Tier 1, for a
specific reason: it's a **push** delivery model — `submit_job` makes
Catalyst issue an HTTP request directly to the worker's `/process`
endpoint — whereas SQS/Azure Queue/Pub-Sub-style adapters would be
**pull** (a worker poll loop). `ExtractionQueue.receive()` therefore
can't be implemented for Catalyst at all; it raises
`NotImplementedError`, and the worker's HTTP handler
(`iac/vendor-native/catalyst/appsail/worker/main.py`) is the real
receive point instead. `ProcessExtractionJobUseCase` was extended to
accept a message directly for exactly this reason — see its docstring.
Porting this capability to another provider means rewriting the
adapter *and* possibly the worker's entrypoint shape, not just
swapping a client library — budget for that if it ever happens.

Job-level retries are configured narrowly (2 retries, 60s apart) to
cover delivery failure only. Retrying a *failed extraction*
automatically isn't implemented — `FAILED` is currently terminal. That
would need a deliberate "requeue for retry" use case, not something to
bolt onto the queue adapter silently.

## Decided: OCR/ML model serving (Zia OCR)

Catalyst's Zia OCR does raw text extraction only — confidence score +
text, no structured field parsing, no line items (confirmed against
the SDK docs, not assumed). There is no Catalyst equivalent of AWS
Textract's Analyze Expense, Azure Form Recognizer's prebuilt-invoice
model, or Google Document AI's Invoice Parser, all of which return
structured invoice fields directly.

Implemented anyway, as `app/adapters/catalyst/ocr_extractor.py` (Zia
OCR) plus `_invoice_text_parser.py` (regex heuristics for vendor name,
invoice number, subtotal/tax/total — line items not attempted).
Deliberately Tier 3 and deliberately low-accuracy: this is an MVP to
get the pipeline working end-to-end on Catalyst's low-cost tier, not a
production-quality extractor. If extraction accuracy turns out to
matter before this ships to real users, the fix is a new
`OcrExtractor` implementation against a purpose-built invoice parser on
another provider — that swap is exactly what the port exists for.
