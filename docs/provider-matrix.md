# Provider matrix

Tracks, per capability, which tier each provider implementation is at.
Update this whenever a capability is added to `blueprint/platform.yaml`
or an adapter is implemented/changed. This is the record that makes
Tier 3 (proprietary) choices deliberate rather than accidental — see
`docs/architecture.md`.

| Capability | Catalyst | AWS | Azure | GCP | Alibaba | Notes |
|---|---|---|---|---|---|---|
| Compute (`linux_http_service`) | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | |
| Relational database | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | Use PostgreSQL for portability where it matters |
| Object storage | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | |
| Secrets | Tier 1 (planned) | not implemented | not implemented | not implemented | not implemented | |
| Events | Tier 3 (default) | not implemented | not implemented | not implemented | not implemented | Only Tier 1 if built on HTTP/webhooks + queue adapter instead of Catalyst Signals/Circuits |
| CI/CD | Tier 1 | Tier 1 | Tier 1 | Tier 1 | Tier 1 | GitHub Actions is the cross-provider control plane |
| Monitoring | Tier 2 (planned) | not implemented | not implemented | not implemented | not implemented | OpenTelemetry export + provider-native dashboards |

Legend: **Tier 1** portable · **Tier 2** equivalent, needs migration/test work · **Tier 3** proprietary, explicit lock-in accepted.

Fill this in as each provider is actually implemented — this table
should describe reality, not intent.
