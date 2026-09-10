# Operations — LedgerLens

Local development
- Create venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r tests/requirements.txt
```

- Run tests:

```bash
pytest -q
```

- Run services locally with Docker Compose (requires Docker):

```bash
docker compose up --build
# api -> http://localhost:9000
```

Configuration
- `application.yaml` contains defaults. Create `local_application.yaml` for local overrides (ignored by Git).
- Environment variables override YAML: `STRATUS_BUCKET`, `WORKER_APPSAIL_ID`, `DATABASE_URL`.

Deployment (Catalyst AppSail)
- Build Docker images from `iac/vendor-native/catalyst/appsail/*/Dockerfile` using the repo root as build context.
- Set AppSail environment variables in the Catalyst console: `STRATUS_BUCKET`, `WORKER_APPSAIL_ID`, `DATABASE_URL`, `X_ZOHO_CATALYST_LISTEN_PORT` (if needed).
- Use Docker Image deployment for AppSail for reliable startup (Catalyst-managed runtime had startup failures in practice).

Troubleshooting
- "Execution failed. Please check the startup command or port." — ensure the service reads `X_ZOHO_CATALYST_LISTEN_PORT` if used, and the startup command doesn't hardcode a port.
- `JobScheduling.jobpool` AttributeError — use `job_scheduling.JOB.submit_job(job_meta)` with `target_id` numeric AppSail id.
- Zia OCR `ML_ERROR` on uploads — ensure file is an `io.BufferedReader` with `.name` and use `model_type` option key.
- `get_object()` returns raw bytes — adapters expect bytes, not response objects.
- Network issues to external Postgres from AppSail — AppSail may block outbound access; use Catalyst Data Store or an in-network proxy.

Monitoring & Recovery
- Add log aggregation (e.g., Papertrail/Sentry) and alerting on job failures and judge rejections.
- Periodic backup of Postgres (if used) or Data Store export via provider tools.

