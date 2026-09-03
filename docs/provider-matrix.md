# Provider matrix

Tracks, per capability, which tier each provider implementation is at.
Update this whenever a capability is added to `blueprint/platform.yaml`
or an adapter is implemented/changed. This is the record that makes
Tier 3 (proprietary) choices deliberate rather than accidental — see
`docs/architecture.md`.

| Capability | Catalyst | AWS | Azure | GCP | Alibaba | Notes |
|---|---|---|---|---|---|---|
| API service (`linux_http_service`) | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | |
| OCR worker (`linux_http_service`, no ingress) | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | Sized separately from the API — see `blueprint/platform.yaml` |
| Object storage (invoice uploads) | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | 90-day retention per contract |
| Queue (`invoice-extraction-jobs`) | Tier 3 (default) | not implemented | not implemented | not implemented | not implemented | Only Tier 1 if built on a portable queue adapter instead of Catalyst Signals/Circuits |
| Relational database | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | PostgreSQL for extracted invoice data |
| Secrets | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | |
| OCR/ML model serving | Tier 3 (default) | not implemented | not implemented | not implemented | not implemented | Model choice (Catalyst QuickML vs. self-hosted OCR model vs. third-party API) not yet decided — record the decision here once made |
| CI/CD | Tier 1 | Tier 1 | Tier 1 | Tier 1 | Tier 1 | GitHub Actions is the cross-provider control plane |
| Monitoring | Tier 2 (planned) | not implemented | not implemented | not implemented | not implemented | OpenTelemetry export + provider-native dashboards |

Legend: **Tier 1** portable · **Tier 2** equivalent, needs migration/test work · **Tier 3** proprietary, explicit lock-in accepted.

Fill this in as each provider is actually implemented — this table
should describe reality, not intent.

## Open decision: OCR/ML model serving

Not yet decided how invoice OCR/extraction is actually performed. This
determines whether the "OCR/ML model serving" row above can ever move
off Tier 3:

- **Catalyst QuickML / Catalyst-native ML tooling** — fastest to ship,
  Tier 3 by definition, no portable equivalent.
- **Self-hosted open-source OCR model** (e.g. a containerized
  layout-aware extraction model) behind the `linux_http_service`
  contract — Tier 1, portable, but more operational work upfront.
- **Third-party OCR/document-AI API** (treated as an external service,
  not cloud infra) — portability question shifts to "can we switch
  vendors," tracked separately from this matrix.

Record the decision here once made, along with the reasoning.
