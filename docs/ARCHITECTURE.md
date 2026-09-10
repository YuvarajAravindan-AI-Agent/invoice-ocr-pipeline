# Architecture — LedgerLens Invoice OCR Pipeline

Overview
- Two primary services: `api` (upload endpoint) and `worker` (extraction). Both run as AppSail services on Zoho Catalyst (AppSail) or as Docker images for local/alternative deployments.
- Cloud primitives (Catalyst): Stratus object storage, Job Scheduling (push delivery), Data Store (Catalyst proprietary relational store). For portability, a `postgres` adapter exists under `app/adapters/postgres/` used for non-Catalyst providers.
- Agentic layer: `ExtractionJudge` uses an LLM (DeepSeek adapter) to validate and decide whether extracted results should be accepted or flagged for human review.

Components
- API service
  - Exposes: `POST /invoices` (upload), `GET /invoices/{id}` (status), `GET /health`
  - Responsibilities: accept upload, store object to Stratus, create invoice record, enqueue job via Job Scheduling.
- Worker service
  - Receives push-delivered job (`/process`), downloads object from Stratus, calls Zia OCR, parses text, runs ExtractionJudge, updates invoice record.
- Storage and DB
  - Stratus: object storage for uploaded invoices.
  - Data Store (Catalyst) or Postgres: invoice metadata and extraction state.
- Job Scheduling
  - Catalyst Job Scheduling issues HTTP push to worker's `/process` endpoint using `JOB.submit_job(...)`.

Key Integrations and Constraints
- Catalyst AppSail network restrictions: AppSail cannot reach arbitrary external Postgres instances on port 5432 (eg, Contabo) and may block outbound HTTPS to non-Catalyst hosts. For Catalyst, use Data Store or a Catalyst-hosted proxy.
- Zia OCR: requires file object to be an `io.BufferedReader` with a `.name` attribute; option key is `model_type` (snake_case).
- JobScheduling constraints: `job_name` limited to 20 chars; only alphanumeric and underscore characters allowed; `target_id` is numeric AppSail service id.

Sequence (request lifecycle)
1. Client POST /invoices -> API
2. API -> Stratus `put_object` (store file)
3. API -> Data Store/Postgres insert invoice (status=PENDING)
4. API -> Job Scheduling `JOB.submit_job(job_meta)` -> worker pushed HTTP
5. Worker `/process` receives job -> download object from Stratus
6. Worker -> Zia OCR -> parse text -> ExtractionJudge
7. Worker -> update invoice in Data Store/Postgres (status=EXTRACTED/NEEDS_REVIEW/FAILED)
8. Client GET /invoices/{id} reads Data Store and returns structured record

Deployment models
- Catalyst-native: uses Data Store + Catalyst SDK adapters; Docker image deployment on AppSail recommended for reliability.
- Portable (AWS/Azure/GCP): use `app/adapters/postgres/` with managed Postgres, Stratus replaced by provider object storage, Job Scheduling replaced by provider queue or webhook.

