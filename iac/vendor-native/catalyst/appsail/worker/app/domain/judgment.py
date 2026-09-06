"""The verdict an ExtractionJudge produces — see
app/application/ports.py's ExtractionJudge protocol. This is the
genuinely agentic step in the pipeline: everything upstream of it
(OCR, regex field parsing, deterministic arithmetic checks in
validation.py) is fixed, rule-based logic. This is the one point where
something reasons about the result and makes a judgment call, instead
of following a hardcoded rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractionJudgment:
    accept: bool  # True: accept automatically. False: flag for human review.
    reasoning: str  # one or two sentences — surfaced to the reviewer, not just logged
    issues: list[str] = field(default_factory=list)
