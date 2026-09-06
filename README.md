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

**Live** on Catalyst — both AppSail services deployed and verified
end-to-end: invoice upload → Stratus object + Data Store row (pending)
→ Job Scheduling push-delivery → worker Zia OCR extraction → DeepSeek
`ExtractionJudge` reasoning over the result → Data Store status update
(`extracted`/`needs_review`/`failed`) → `GET` returning the full
record. The judge has caught real extraction errors in practice — e.g.
flagging a vendor name that was actually the document heading, and
missed subtotal/tax/total fields the OCR text clearly contained.

- `api`: https://api-50045555479.development.catalystappsail.in
- `worker`: https://worker-50045555479.development.catalystappsail.in
  (internal — receives Job Scheduling's push delivery, not meant to be
  called directly)

Uses Catalyst Data Store, not the `app/adapters/postgres/` adapter —
see [iac/vendor-native/catalyst/README.md](iac/vendor-native/catalyst/README.md)
for why. `catalyst.json` is committed; each service's environment
variables are set via the Catalyst console (not `app-config.json`,
which doesn't apply to Docker Image AppSail services).

Catalyst is the only active provider in `deploy/provider-matrix.yaml`;
AWS/Azure/GCP/Alibaba are present but `active: false` until validated
per §10 of the architecture doc — those would use `app/adapters/postgres/`.
