# adapters/catalyst

Concrete implementations of the ports defined in `../../application/`,
using the Catalyst Python SDK (`zcatalyst-sdk`). This is the only place
Catalyst-specific client code should appear — the domain layer must
never import it directly. `InvoiceRepository` is *not* here — see
`../postgres/README.md` for why.

| Port | Implementation | Notes |
|---|---|---|
| `ObjectStore` | `object_store.py` — `CatalystStratusObjectStore` | Stratus |
| `SecretProvider` | `secret_provider.py` — `CatalystEnvSecretProvider` | AppSail env vars — Catalyst has no separate secret-manager SDK component |
| `OcrExtractor` | `ocr_extractor.py` — `CatalystZiaOcrExtractor` | Zia OCR (raw text only) + regex heuristics in `_invoice_text_parser.py`. Low accuracy by design — see that file's docstring |
| `ExtractionQueue` | `job_queue.py` — `CatalystJobQueue` | Job Scheduling. **Push, not pull** — `receive()` raises `NotImplementedError`; the worker's HTTP handler is the real receive point |

Required environment variables (set in each AppSail service's
`app-config.json`, not committed with real values):

- `STRATUS_BUCKET` — bucket name for `CatalystStratusObjectStore`
- `DATABASE_URL` — Postgres connection string, read via `CatalystEnvSecretProvider`
- `WORKER_APPSAIL_ID` — the worker service's registered name, needed by `CatalystJobQueue.enqueue()` (API service only)

`bucket.get_object()` returns raw bytes directly (confirmed via a real
`AttributeError` caught in production, not docs — the response is not
wrapped in an object with a `.content` attribute as the docs implied).
`app.zia()` as the OCR accessor name is confirmed working.

