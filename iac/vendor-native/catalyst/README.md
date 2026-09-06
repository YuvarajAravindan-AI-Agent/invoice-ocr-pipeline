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
| `data.relational_database` | External managed PostgreSQL (not Catalyst Data Store) | Blueprint asks for PostgreSQL specifically for portability; Catalyst Data Store is NoSQL and would be Tier 3. Implemented once, shared across providers — `app/adapters/postgres/` |
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
values, never committed:

| Variable | api | worker | Used by |
|---|:-:|:-:|---|
| `STRATUS_BUCKET` | ✓ | ✓ | `CatalystStratusObjectStore` |
| `DATABASE_URL` | ✓ | ✓ | `PostgresInvoiceRepository`, via `CatalystEnvSecretProvider` |
| `WORKER_APPSAIL_ID` | ✓ | — | `CatalystJobQueue.enqueue()` — the worker's registered AppSail service name |
| `DEEPSEEK_API_KEY` | — | ✓ | `DeepSeekExtractionJudge` — see `../../../app/adapters/deepseek/README.md` |

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
- **`catalyst.json` and both `app-config.json` files are not committed.** They're CLI-generated and account-specific (see "One-time setup" above) — this repo was previously deployed and run end-to-end against a real Catalyst project's live SDK (see the "Fix real Catalyst SDK bugs found deploying api/worker to live AppSail" commit), but that generated config was local-only and was never checked in, and the AppSail services it pointed at are no longer responding. Regenerating them via `catalyst init`/`appsail:add` is required before this can be redeployed.

## Sources

- [CLI command reference](https://docs.catalyst.zoho.com/en/cli/v1/cli-command-reference/)
- [Deploy options (`--only`/`--except`/`--ignore-scripts`)](https://docs.catalyst.zoho.com/en/cli/v1/deploy-resources/deploy-options/)
- [Add an AppSail service](https://docs.catalyst.zoho.com/en/cli/v1/add-appsail/)
- [Python SDK components](https://docs.catalyst.zoho.com/en/sdk/python/v1/components/)
- [Stratus upload/download](https://docs.catalyst.zoho.com/en/sdk/python/v1/cloud-scale/stratus/upload-object/)
- [Job Scheduling implementation](https://docs.catalyst.zoho.com/en/job-scheduling/help/implementation/submit-jobs-using-jobs/)
- [Zia OCR](https://docs.catalyst.zoho.com/en/sdk/python/v1/zia/ocr/)
