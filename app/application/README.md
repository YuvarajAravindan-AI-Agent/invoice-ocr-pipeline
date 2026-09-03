# application

Use cases and **ports** — the interfaces the domain layer depends on,
e.g. `ObjectStore.put()`, `SecretProvider.get()`, `EventBus.publish()`,
`JobScheduler.schedule()`. Each port gets one implementation per
provider under `../adapters/<provider>/`. Define the port here even
before a second adapter exists — that's what keeps the first
implementation from silently becoming the only one that's possible.

## Ports (`ports.py`)

`ObjectStore`, `InvoiceRepository`, `ExtractionQueue`, `OcrExtractor`,
`SecretProvider`. No implementations exist yet — `../adapters/*/` are
still empty. `OcrExtractor` is the seam for the still-open "OCR/ML
model serving" decision in `../../docs/provider-matrix.md`.

## Use cases (`use_cases/`)

- `SubmitInvoiceUseCase` — API service: store upload, create the invoice record, enqueue extraction.
- `ProcessExtractionJobUseCase` — worker: pull one job, extract, validate, update the record.
- `GetInvoiceStatusUseCase` — API service: read back status/results.

Tested against in-memory fakes (not real adapters) in `../../tests/unit/`.
