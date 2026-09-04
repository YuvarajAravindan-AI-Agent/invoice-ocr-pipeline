"""ExtractionJudge implemented against the DeepSeek API — the one
genuinely agentic step in this pipeline. Everything upstream (Zia OCR,
the regex field parser in app/adapters/catalyst/_invoice_text_parser.py,
the deterministic arithmetic checks in app/domain/validation.py) is
fixed logic with no judgment involved. This adapter is different: it
hands the model the raw OCR text, the fields a regex parser pulled out
of it, and what the deterministic checks already flagged, and lets the
model *decide* — accept automatically, or flag for human review, with
its own reasoning — rather than following a hardcoded confidence
threshold.

DeepSeek's API is OpenAI-compatible (same request/response shape as
the OpenAI Chat Completions API, just a different base_url), so this
uses the `openai` SDK rather than a DeepSeek-specific one — confirmed
against a live call, not assumed from docs: forced function calling via
tool_choice={"type": "function", "function": {"name": ...}} works
exactly like OpenAI's, returning a tool_calls entry with a JSON string
in .function.arguments (not a typed .input dict like Anthropic's
tool_use blocks — that JSON has to be parsed explicitly).
"""

from __future__ import annotations

import json

from app.domain.extraction import ExtractionResult
from app.domain.judgment import ExtractionJudgment

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"

_SUBMIT_JUDGMENT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_judgment",
        "description": (
            "Submit your judgment on whether this invoice extraction should be "
            "accepted automatically or flagged for human review."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "accept": {
                    "type": "boolean",
                    "description": "true to accept automatically, false to flag for human review",
                },
                "reasoning": {
                    "type": "string",
                    "description": "One or two sentences explaining the decision, written for a human reviewer",
                },
                "issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific problems found beyond what was already flagged; empty if none",
                },
            },
            "required": ["accept", "reasoning", "issues"],
        },
    },
}

_PROMPT_TEMPLATE = """You are reviewing an automated invoice OCR extraction before it's \
accepted into an accounting system. The fields below were pulled out of the raw OCR text \
by a regex-based parser, which is known to be unreliable — your job is to catch what it \
got wrong, not just rubber-stamp it.

Raw OCR text:
---
{raw_text}
---

Fields the parser extracted:
  vendor_name: {vendor_name}
  invoice_number: {invoice_number}
  subtotal: {subtotal}
  tax: {tax}
  total: {total}
  confidence_score: {confidence_score}

Deterministic checks already flagged: {deterministic_issues}

Decide whether to accept these fields automatically or flag for human review. Consider:
- Does vendor_name look like a plausible company name, or could it be OCR noise / a \
document heading mistaken for a vendor?
- Does invoice_number look like a real invoice identifier?
- Does anything in the raw OCR text contradict the extracted fields (e.g. a different \
total appears in the text than what was parsed)?
- Are the deterministic checks above pointing at something that actually matters, or are \
they noise (e.g. a missing tax field on an invoice that plausibly has no tax)?

Call submit_judgment with your decision."""


class DeepSeekExtractionJudge:
    def __init__(self, api_key: str, model: str = "deepseek-chat") -> None:
        # Imported lazily so importing this module doesn't require the
        # openai package unless this adapter is actually constructed
        # (matches the lazy-import style already used for the SDK in
        # app/adapters/catalyst/*.py's per-request initialize() pattern).
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=_DEEPSEEK_BASE_URL)
        self._model = model

    def judge(self, result: ExtractionResult, deterministic_issues: list[str]) -> ExtractionJudgment:
        prompt = _PROMPT_TEMPLATE.format(
            raw_text=(result.raw_text or "(no raw OCR text available)")[:4000],
            vendor_name=result.vendor_name,
            invoice_number=result.invoice_number,
            subtotal=result.subtotal,
            tax=result.tax,
            total=result.total,
            confidence_score=f"{result.confidence_score:.2f}",
            deterministic_issues=deterministic_issues or "none",
        )

        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=500,
            tools=[_SUBMIT_JUDGMENT_TOOL],
            tool_choice={"type": "function", "function": {"name": "submit_judgment"}},
            messages=[{"role": "user", "content": prompt}],
        )

        tool_call = response.choices[0].message.tool_calls[0]
        data = json.loads(tool_call.function.arguments)

        return ExtractionJudgment(
            accept=bool(data["accept"]),
            reasoning=str(data["reasoning"]),
            issues=list(data.get("issues", [])),
        )
