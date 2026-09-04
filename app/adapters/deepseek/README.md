# adapters/deepseek

Not a per-cloud-provider adapter like `../catalyst/` — `ExtractionJudge`
is implemented once here against the DeepSeek API, the same way
`../postgres/` implements `InvoiceRepository` once regardless of which
cloud the rest of the pipeline runs on. This is the pipeline's one
genuinely agentic component: everything else (Zia OCR, the regex field
parser, the deterministic checks in `app/domain/validation.py`) is
fixed logic — this is where a model actually reasons about the result
and decides accept vs. flag, instead of following a hardcoded rule.

| Port | Implementation | Notes |
|---|---|---|
| `ExtractionJudge` | `extraction_judge.py` — `DeepSeekExtractionJudge` | Uses the `openai` SDK against DeepSeek's OpenAI-compatible API (`base_url=https://api.deepseek.com`), with forced function calling via `tool_choice` so the decision comes back as a structured object, not prose to parse — confirmed against a live call, not assumed from docs. |

## Required environment variable

- `DEEPSEEK_API_KEY` — read via each provider's `SecretProvider`
  (`CatalystEnvSecretProvider` on Catalyst). Set on the **worker**
  service only — the `api` service never constructs this adapter.

## Model

Defaults to `deepseek-chat`. Confirmed via a live API call to resolve
to `deepseek-v4-flash` server-side as of 2026-09-04 — DeepSeek may
repoint the `deepseek-chat` alias to newer models over time without
notice, which is expected/desired behavior for this use case (fast,
cheap judgment calls, not a pinned-model requirement).

## Failure behavior

If the API call fails (rate limit, network, bad key, or the response
doesn't contain the expected tool call), the use case
(`ProcessExtractionJobUseCase`) catches it and falls back to the
deterministic `validate_extraction()` result alone — the agentic layer
degrades gracefully to the pre-existing rule-based behavior rather than
failing the whole job. See `process_extraction_job.py`.
