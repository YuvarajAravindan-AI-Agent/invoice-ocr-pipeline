# Architecture

Catalyst-first, multi-cloud-portable design for this service. Full
rationale: `portable-multicloud-catalyst-architecture.docx` (design
reference, not tracked in this repo).

## Executive position

Use a neutral architecture contract and portable application interfaces
as the long-lived design. Use Terraform/OpenTofu modules, Catalyst
configuration, and provider SDKs as replaceable adapters. Do not attempt
to make one file directly deploy every cloud resource identically;
instead, keep one intent and maintain small, explicit provider
implementations.

## Portability tiers

| Tier | Meaning | Expected effort |
|---|---|---|
| 1 — portable | Rebuildable with the same app image, schema, and contract | Provider adapter and configuration only |
| 2 — equivalent | Same business behavior, different managed-service semantics | Adapter plus migration/test work |
| 3 — proprietary | Catalyst-native or cloud-native capability with no exact twin | Replacement design and explicit lock-in acceptance |

Every Catalyst-native service used in `iac/vendor-native/catalyst/`
(Functions, AppSail, Data Store, Stratus, Signals, Pipelines) starts as
Tier 3 by default. Record the actual tier, export path, and replacement
plan for each one in `docs/provider-matrix.md` — don't leave it implicit.

## Non-goals

- Perfect one-to-one equivalence between proprietary managed services.
- Automatic conversion of Catalyst-native services into identical
  services elsewhere.
- Multi-cloud active-active operation from day one.
- Hiding provider trade-offs behind an abstraction so aggressively that
  important capabilities disappear.

## Repository structure

See the root [README.md](../README.md) for the full layout. The two
things worth restating here:

- **`iac/vendor-native/`** and **`iac/opentofu/`** are deliberately two
  separate implementations of the same intent (`blueprint/`), not one
  trying to generate the other. Keep them independently reviewable.
- **`app/domain/` never imports a cloud SDK.** Everything provider
  -specific lives in `app/adapters/<provider>/`, behind a port defined
  in `app/application/`.

## CI/CD

`.github/workflows/iac-pipeline.yml` reads `deploy/provider-matrix.yaml`
and runs, per active provider: quality gates once (shared) → plan (every
PR) → manual approval via a per-provider GitHub Environment → apply (on
merge to `main`) → smoke tests → release evidence artifact.

## Security minimums

- Separate human identity, CI identity, and runtime identity; least
  privilege per environment.
- OIDC/federated short-lived credentials for CI, never long-lived keys
  in GitHub secrets.
- Encrypted remote IaC state with locking, per provider/environment —
  never share state files across clouds.
- No credentials, project IDs, or account IDs in `blueprint/`.

## Migration workflow (if this service ever needs to move off Catalyst)

1. Freeze `blueprint/` and record the current Catalyst deployment version.
2. Export data, object metadata, configuration names, and event subscriptions.
3. Provision the destination via its `iac/opentofu/<provider>/` adapter.
4. Deploy the same application image, then run database migrations.
5. Import data; verify counts, checksums, referential integrity, business workflows.
6. Run smoke, contract, security, performance, and restore tests.
7. Switch traffic via DNS/gateway controls; keep Catalyst in a rollback window.
8. Update `docs/provider-matrix.md` with what actually happened.
