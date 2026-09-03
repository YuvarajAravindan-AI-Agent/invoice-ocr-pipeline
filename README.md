# service-template

Template repo for any new service (cloud app, ML service, devops
tooling, cloud infra module). Built Catalyst-first, with a documented,
testable route to AWS, Azure, GCP, Alibaba, or any future provider.

## Using this template

1. Click **Use this template** on GitHub (or `gh repo create <name> --template YuvarajAravindan-AI-Agent/service-template`).
2. Replace every `<service-name>` / `<region>` placeholder in [deploy/provider-matrix.yaml](deploy/provider-matrix.yaml).
3. Fill in [blueprint/platform.yaml](blueprint/platform.yaml) with the new service's actual capability requirements.
4. Implement `iac/vendor-native/catalyst/` first (Catalyst is the default primary target — see `tier: primary` in the manifest).
5. Add OpenTofu adapters under `iac/opentofu/<provider>/` only for the providers you're actually validating against; leave the rest `active: false`.
6. If the service has application code, put cloud-SDK-free logic in `app/domain/` and `app/application/`, and cloud-specific calls only in `app/adapters/<provider>/`.

## Layout

| Path | Purpose |
|---|---|
| `blueprint/` | The neutral capability contract — the one thing that's true regardless of provider. |
| `app/` | Ports-and-adapters application code (skip if this is a pure infra/devops repo). |
| `iac/vendor-native/` | **Copy 1** — the Catalyst-specific implementation, driven by `catalyst-cli`. |
| `iac/opentofu/` | **Copy 2** — the vendor-neutral implementation, one subfolder per cloud, common module in `iac/opentofu/modules/common`. |
| `deploy/provider-matrix.yaml` | Single source of truth for which providers are active; drives the CI job matrix. |
| `scripts/adapters/` | Uniform `plan/apply/destroy` wrappers — one per mechanism (`opentofu`, `catalyst-cli`). |
| `tests/` | Contract validation, smoke tests, and portability drills (§10 of the architecture doc). |
| `docs/` | Architecture notes and the provider tier matrix for this specific service. |
| `.github/workflows/iac-pipeline.yml` | Plans every active provider on PR, applies on merge to `main`, each gated by its own GitHub Environment approval. |

## Adding a new cloud provider

1. Add a block to `deploy/provider-matrix.yaml` (`active: false` to start).
2. Implement `iac/opentofu/<provider>/` against the common variable contract in `iac/opentofu/modules/common`.
3. Create a GitHub Environment named `<provider>-prod` with required reviewers.
4. Flip `active: true`. Nothing else changes — the pipeline picks it up automatically.

See [docs/architecture.md](docs/architecture.md) for the full design rationale and [docs/provider-matrix.md](docs/provider-matrix.md) for this service's current tier assignments.
