# iac/vendor-native/catalyst

Copy 1 — the Catalyst-specific implementation, driven by `catalyst-cli`
via `../../../scripts/adapters/catalyst.sh`. Grounded against the
current Catalyst CLI docs (docs.catalyst.zoho.com, checked 2026-09-03)
— see sources at the bottom.

## What this maps to, per blueprint/platform.yaml

| Blueprint capability | Catalyst service | Why |
|---|---|---|
| `compute` (API, 2 vCPU/4 GiB, HTTPS ingress) | AppSail, custom Docker runtime | AppSail supports configurable resources and a custom OCI image; Functions are sized for lighter, shorter-lived workloads |
| `compute.worker` (OCR worker, 4 vCPU/8 GiB, no ingress) | AppSail, custom Docker runtime | Same reasoning — this is the expensive part of the service |
| `storage.object_storage` | Stratus | Referenced from application code via the Catalyst SDK, not IaC'd as a file here |
| `data.relational_database` | External managed PostgreSQL (not Catalyst Data Store) | Blueprint asks for PostgreSQL specifically for portability; Catalyst Data Store is NoSQL and would be Tier 3 |
| `queue` (`invoice-extraction-jobs`) | **Not decided** | See `../../../docs/provider-matrix.md` — Catalyst has no confirmed native queue primitive equivalent to SQS; needs a decision before this can be implemented |

## Directory layout (target state)

```
iac/vendor-native/catalyst/
├── catalyst.json          # NOT hand-authored — see "One-time setup" below
├── .catalystrc             # NOT hand-authored — CLI-generated, gitignored (local auth cache)
├── appsail/
│   ├── api/
│   │   ├── app-config.json # NOT hand-authored — see below
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── main.py
│   └── worker/
│       ├── app-config.json
│       ├── Dockerfile
│       ├── requirements.txt
│       └── worker.py
```

`Dockerfile`/`requirements.txt`/`main.py`/`worker.py` are scaffolded in
this commit as minimal placeholders (health-check only, no real
extraction logic yet). `catalyst.json` and each `app-config.json` are
**not** — see below.

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

After generation, edit `app-config.json` for each service to set the
memory/startup command matching `blueprint/platform.yaml`
(`compute.cpu`/`memory_gib` for api, `compute.worker.*` for worker) —
the docs confirm these fields are editable post-generation but don't
publish the full field schema, so match whatever keys the CLI actually
generates rather than the blueprint's naming.

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
- **Queue capability is unresolved** — see `docs/provider-matrix.md`.

## Sources

- [CLI command reference](https://docs.catalyst.zoho.com/en/cli/v1/cli-command-reference/)
- [Deploy options (`--only`/`--except`/`--ignore-scripts`)](https://docs.catalyst.zoho.com/en/cli/v1/deploy-resources/deploy-options/)
- [Add an AppSail service](https://docs.catalyst.zoho.com/en/cli/v1/add-appsail/)
- [Functions directory structure](https://docs.catalyst.zoho.com/en/cli/v1/project-directory-structure/functions-directory/)
