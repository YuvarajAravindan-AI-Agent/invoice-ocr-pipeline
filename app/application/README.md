# application

Use cases and **ports** — the interfaces the domain layer depends on,
e.g. `ObjectStore.put()`, `SecretProvider.get()`, `EventBus.publish()`,
`JobScheduler.schedule()`. Each port gets one implementation per
provider under `../adapters/<provider>/`. Define the port here even
before a second adapter exists — that's what keeps the first
implementation from silently becoming the only one that's possible.

## Ports (`ports.py`)

`ObjectStore`, `InvoiceRepository`, `ExtractionQueue`, `OcrExtractor`,
`SecretProvider`, `ExtractionJudge`. Implemented in `../adapters/*/` —
`ExtractionJudge` in particular is the pipeline's one genuinely agentic
seam: everything else here is deterministic (OCR call, regex field
parsing, fixed arithmetic checks in `../domain/validation.py`) —
`ExtractionJudge` is where an LLM actually reasons about the result and
decides accept vs. flag, instead of a hardcoded rule. See
`../adapters/anthropic/README.md`.

## Use cases (`use_cases/`)

- `SubmitInvoiceUseCase` — API service: store upload, create the invoice record, enqueue extraction.
- `ProcessExtractionJobUseCase` — worker: pull one job, extract, run the deterministic checks *and* the agentic judge, update the record. The judge's `accept` decision — not the deterministic checks alone — determines EXTRACTED vs. NEEDS_REVIEW; the deterministic checks are passed to it as context and used as a fallback if the judge call fails.
- `GetInvoiceStatusUseCase` — API service: read back status/results.

Tested against in-memory fakes (not real adapters) in `../../tests/unit/`.
