# invoice-ocr-pipeline

ML service for automated invoice data extraction: accepts uploaded
invoices (PDF/image), runs OCR + extraction, returns structured data
(vendor, line items, totals, confidence scores).

Instantiated from [service-template](https://github.com/YuvarajAravindan-AI-Agent/service-template) —
Catalyst-first, with a documented, testable route to AWS, Azure, GCP, or
Alibaba if this ever needs to move. See [docs/architecture.md](docs/architecture.md)
for the full design rationale and [docs/provider-matrix.md](docs/provider-matrix.md)
for this service's current tier assignments.

## Layout

| Path | Purpose |
|---|---|
| `blueprint/` | Neutral capability contract — API service, OCR worker, object storage, queue, relational DB. |
| `app/` | Ports-and-adapters application code — domain/extraction logic stays free of cloud SDKs. |
| `iac/vendor-native/` | Catalyst-specific implementation (primary target), driven by `catalyst-cli`. |
| `iac/opentofu/` | Vendor-neutral implementation, one subfolder per cloud — not yet implemented for any provider. |
| `deploy/provider-matrix.yaml` | Single source of truth for which providers are active; drives the CI job matrix. |
| `tests/` | Contract validation, smoke tests, and portability drills. |

## Status

`app/` (ports-and-adapters domain/application code, Catalyst and
Postgres adapters, and a DeepSeek-based `ExtractionJudge`) is
implemented and was verified end-to-end against live Catalyst infra:
invoice upload → Postgres row + Stratus object → Job Scheduling
push-delivery → worker Zia OCR extraction → Postgres status update,
with real extracted fields (confidence 0.99).

There is currently no live URL — `catalyst.json` and each service's
`app-config.json` are account/CLI-generated and were never committed,
so the deployment from that verification run isn't reproducible from
this repo as-is. See [iac/vendor-native/catalyst/README.md](iac/vendor-native/catalyst/README.md)'s
"One-time setup" and "Known gaps" for what's needed to redeploy.

Catalyst is the only active provider in `deploy/provider-matrix.yaml`;
AWS/Azure/GCP/Alibaba are present but `active: false` until validated
per §10 of the architecture doc.
