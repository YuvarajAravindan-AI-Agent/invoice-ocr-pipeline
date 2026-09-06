# adapters/anthropic

Not a per-cloud-provider adapter like `../catalyst/` — `ExtractionJudge`
is implemented once here against the Claude API, the same way
`../postgres/` implements `InvoiceRepository` once regardless of which
cloud the rest of the pipeline runs on. This is the pipeline's one
genuinely agentic component: everything else (Zia OCR, the regex field
parser, the deterministic checks in `app/domain/validation.py`) is
fixed logic — this is where a model actually reasons about the result
and decides accept vs. flag, instead of following a hardcoded rule.

| Port | Implementation | Notes |
|---|---|---|
| `ExtractionJudge` | `extraction_judge.py` — `ClaudeExtractionJudge` | Uses forced tool-use (`tool_choice`) so the decision comes back as a structured object, not prose to parse |

## Required environment variable

- `ANTHROPIC_API_KEY` — read via each provider's `SecretProvider`
  (`CatalystEnvSecretProvider` on Catalyst). Set on the **worker**
  service only — the `api` service never constructs this adapter.

## Model

Defaults to `claude-haiku-4-5` — fast and cheap enough to run on every
extraction without materially changing the pipeline's cost profile.
Override via the adapter's `model` constructor argument if a
higher-reasoning model is ever needed for harder documents.

## Failure behavior

If the API call fails (rate limit, network, bad key), the use case
(`ProcessExtractionJobUseCase`) catches it and falls back to the
deterministic `validate_extraction()` result alone — the agentic layer
degrades gracefully to the pre-existing rule-based behavior rather than
failing the whole job. See `process_extraction_job.py`.
