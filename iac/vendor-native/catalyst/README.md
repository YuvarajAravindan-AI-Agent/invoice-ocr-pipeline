# iac/vendor-native/catalyst

Copy 1 — the Catalyst-specific implementation, driven by `catalyst-cli`
via `../../../scripts/adapters/catalyst.sh`. Grounded against the
current Catalyst CLI/SDK docs (docs.catalyst.zoho.com, checked
2026-09-03) — see sources at the bottom.

## What this maps to, per blueprint/platform.yaml

| Blueprint capability | Catalyst service | Why |
|---|---|---|
| `compute` (API, 2 vCPU/4 GiB, HTTPS ingress) | AppSail, custom Docker runtime | AppSail supports configurable resources and a custom OCI image; Functions are sized for lighter, shorter-lived workloads |
| `compute.worker` (OCR worker, 4 vCPU/8 GiB, no ingress) | AppSail, custom Docker runtime | Same reasoning — this is the expensive part of the service |
| `storage.object_storage` | Stratus | `app/adapters/catalyst/object_store.py` |
| `data.relational_database` | Catalyst Data Store (**revised** — see below) | Originally external managed PostgreSQL for portability (`app/adapters/postgres/`, still used by that name for AWS/Azure/GCP/Alibaba). Reverted to Data Store for Catalyst specifically after confirming against a live deploy that AppSail's outbound network rejects both raw Postgres (5432) and general outbound HTTPS to a non-Catalyst host — see `app/adapters/catalyst/invoice_repository.py`. Explicit Tier 3 lock-in, not an oversight — see `../../../docs/provider-matrix.md` |
| `queue` (`invoice-extraction-jobs`) | Job Scheduling | **Decided** — see `../../../docs/provider-matrix.md`. Push delivery (Catalyst POSTs to the worker), not pull — changes the worker's entrypoint shape, see below |
| OCR/extraction | Zia OCR + regex heuristics | **Decided** — see `../../../docs/provider-matrix.md`. Raw text only, no structured fields; deliberately low-accuracy MVP |

## Directory layout (current state)

```
iac/vendor-native/catalyst/
├── catalyst.json          # NOT hand-authored — see "One-time setup" below
├── .catalystrc             # NOT hand-authored — CLI-generated, gitignored (local auth cache)
├── appsail/
│   ├── api/
│   │   ├── app-config.json # NOT hand-authored — see below
│   │   ├── Dockerfile      # builds from REPO ROOT context — see the Dockerfile itself
│   │   ├── requirements.txt
│   │   └── main.py         # real: submit/status endpoints wired to the use cases
│   └── worker/
│       ├── app-config.json
│       ├── Dockerfile      # builds from REPO ROOT context
│       ├── requirements.txt
│       └── main.py         # real: /process endpoint, the actual "receive" point for jobs
```

`main.py` in both services is wired to the real use cases in
`app/application/use_cases/` via the adapters in `app/adapters/catalyst/`
and `app/adapters/postgres/`. `catalyst.json` and each `app-config.json`
are **not** committed yet — see below.

Both Dockerfiles must be built with the **repo root** as context, not
their own directory, since they need `app/`:

```
docker build -f iac/vendor-native/catalyst/appsail/api/Dockerfile -t invoice-ocr-pipeline-api:latest .
docker build -f iac/vendor-native/catalyst/appsail/worker/Dockerfile -t invoice-ocr-pipeline-worker:latest .
```

## One-time setup (needs to happen at your keyboard, not mine)

`catalyst init` and `catalyst appsail:add` are interactive, and they
create real resources against your Catalyst account
(`yuvarajaravindan@ai-agentic-enterprises.com`). I can't run these for
you — doing so without you present would be provisioning cloud
resources under your identity blind. Run, from this directory:

```
npm install -g zcatalyst-cli
catalyst login --dc in
catalyst init
#   -> select your portal
#   -> create/select a project for invoice-ocr-pipeline
#   -> select AppSail
#   -> choose "Custom Runtime (Docker)" when prompted
#   -> service name: api

catalyst appsail:add
#   -> repeat for the worker service, custom runtime, name: worker
```

This generates the real `catalyst.json`, `.catalystrc`, and
`app-config.json` files with the correct schema for your account/DC —
commit `catalyst.json` and both `app-config.json` files (not
`.catalystrc`, which is local auth state — already in `.gitignore`).

After generation, edit `app-config.json` for each service to set:
- memory/CPU matching `blueprint/platform.yaml` (`compute.*` for api, `compute.worker.*` for worker) — exact field names not published, match whatever the CLI generates
- environment variables (see below)

## Required environment variables per service

Set these in each service's `app-config.json` after generation — real
values, never committed. For Docker Image AppSail services (this
project's actual deployment mode), `app-config.json` doesn't exist —
these have to be set via the Catalyst console's Configuration section,
or baked into the image at build time (`docker build --build-arg`),
never written into the committed Dockerfile.

| Variable | api | worker | Used by |
|---|:-:|:-:|---|
| `STRATUS_BUCKET` | ✓ | ✓ | `CatalystStratusObjectStore` |
| `WORKER_APPSAIL_ID` | ✓ | — | `CatalystJobQueue.enqueue()` — the worker's registered AppSail service name |
| `DEEPSEEK_API_KEY` | — | ✓ | `DeepSeekExtractionJudge` — see `../../../app/adapters/deepseek/README.md` |

No `DATABASE_URL`/connection-string secret at all for this provider —
`CatalystDataStoreInvoiceRepository` (`app/adapters/catalyst/invoice_repository.py`)
talks to Data Store through the same `catalyst_app` SDK instance
already used for Stratus/Zia, not a network connection with its own
credential.

**Why Data Store instead of external PostgreSQL, despite the
portability cost:** tried an external Postgres first (on a Contabo
box), confirmed against a live deploy that Catalyst AppSail's outbound
network rejects raw Postgres (port 5432) — the exact same image that
queries Postgres fine via `docker run` locally gets a fast (~1s)
gateway-level 500 on Catalyst. Tried fronting that same Postgres with
an HTTPS reverse proxy (PostgREST + Caddy) next, on the theory that
only 5432 was blocked — same fast 500 over HTTPS too, pointing at a
broader outbound restriction on AppSail rather than a port-specific
one. Data Store sidesteps the question entirely since it's an
in-platform call, not an outbound one. **One-time manual step**: the
`invoices` table and its columns must be created via the Catalyst
console first — see the docstring in `app/adapters/catalyst/invoice_repository.py`
for the exact column list and types (no CLI/SDK path exists for Data
Store table creation, confirmed against Zoho's own docs).

## CI auth

`scripts/adapters/catalyst.sh` expects these as environment variables
(wired in `.github/workflows/iac-pipeline.yml` from repo/environment
secrets — not set up yet, see below):

- `CATALYST_CI_TOKEN` — generate with `catalyst token:generate` locally, store as a GitHub secret
- `CATALYST_PROJECT_ID` — from `catalyst project:list` after the setup above
- `CATALYST_DEPLOY_TARGETS` — already set in `deploy/provider-matrix.yaml` (`appsail:api,appsail:worker`)

Not yet created: the `catalyst-prod` GitHub Environment and the two
secrets above.

## Known gaps (don't paper over these)

- **No dry-run/plan flag exists in the Catalyst CLI.** `scripts/adapters/catalyst.sh plan` can only validate that `catalyst.json` exists locally — it cannot show what would change before deploying. Review for a Catalyst change has to come from the PR diff of the config files themselves.
- **No `appsail:delete` command is documented.** `scripts/adapters/catalyst.sh destroy` can remove Functions via `functions:delete` but AppSail services must be deleted through the Catalyst console.
- **Two SDK details assumed, not confirmed**: the byte-content attribute on `bucket.get_object()`'s response, and `app.zia()` as the OCR accessor. Flagged inline in the adapter code — verify once the SDK is actually runnable against a real project.
- **Failed extractions don't auto-retry.** `FAILED` is a terminal status; there's no requeue mechanism yet.
- **`catalyst.json` is committed** (regenerated via `catalyst appsail:add`, Docker Image source pointing at `localhost/invoice-ocr-pipeline-{api,worker}:latest`) — deploy with `catalyst deploy appsail --name <api|worker> --source docker://localhost/invoice-ocr-pipeline-<name>:latest --port 9000 -ni` after `docker build`ing both images from the repo root. `app-config.json` doesn't apply to Docker Image AppSail services at all; environment variables are set via the console's Configuration tab per service instead — see the table above.

## Sources

- [CLI command reference](https://docs.catalyst.zoho.com/en/cli/v1/cli-command-reference/)
- [Deploy options (`--only`/`--except`/`--ignore-scripts`)](https://docs.catalyst.zoho.com/en/cli/v1/deploy-resources/deploy-options/)
- [Add an AppSail service](https://docs.catalyst.zoho.com/en/cli/v1/add-appsail/)
- [Python SDK components](https://docs.catalyst.zoho.com/en/sdk/python/v1/components/)
- [Stratus upload/download](https://docs.catalyst.zoho.com/en/sdk/python/v1/cloud-scale/stratus/upload-object/)
- [Job Scheduling implementation](https://docs.catalyst.zoho.com/en/job-scheduling/help/implementation/submit-jobs-using-jobs/)
- [Zia OCR](https://docs.catalyst.zoho.com/en/sdk/python/v1/zia/ocr/)
