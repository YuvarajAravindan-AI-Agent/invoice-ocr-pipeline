"""ExtractionJudge implemented against the Claude API — the one
genuinely agentic step in this pipeline. Everything upstream (Zia OCR,
the regex field parser in app/adapters/catalyst/_invoice_text_parser.py,
the deterministic arithmetic checks in app/domain/validation.py) is
fixed logic with no judgment involved. This adapter is different: it
hands the model the raw OCR text, the fields a regex parser pulled out
of it, and what the deterministic checks already flagged, and lets the
model *decide* — accept automatically, or flag for human review, with
its own reasoning — rather than following a hardcoded confidence
threshold.

Uses tool use (forced via tool_choice) rather than asking for JSON in
prose, so the decision comes back as a structured, reliably-parseable
object instead of something that needs regex/markdown-fence stripping
to parse.
"""

from __future__ import annotations

from app.domain.extraction import ExtractionResult
from app.domain.judgment import ExtractionJudgment

_SUBMIT_JUDGMENT_TOOL = {
    "name": "submit_judgment",
    "description": (
        "Submit your judgment on whether this invoice extraction should be "
        "accepted automatically or flagged for human review."
    ),
    "input_schema": {
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


class ClaudeExtractionJudge:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5") -> None:
        # Imported lazily so importing this module doesn't require the
        # anthropic package unless this adapter is actually constructed
        # (matches the lazy-import style already used for the SDK in
        # app/adapters/catalyst/*.py's per-request initialize() pattern).
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
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

        response = self._client.messages.create(
            model=self._model,
            max_tokens=500,
            tools=[_SUBMIT_JUDGMENT_TOOL],
            tool_choice={"type": "tool", "name": "submit_judgment"},
            messages=[{"role": "user", "content": prompt}],
        )

        tool_use = next(block for block in response.content if block.type == "tool_use")
        data = tool_use.input

        return ExtractionJudgment(
            accept=bool(data["accept"]),
            reasoning=str(data["reasoning"]),
            issues=list(data.get("issues", [])),
        )
