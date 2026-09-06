"""Business rules for deciding whether an extraction result is trustworthy
enough to accept automatically, or needs human review. Pure functions —
no I/O, no ports.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.extraction import ExtractionResult

AMOUNT_TOLERANCE = Decimal("0.01")
MIN_CONFIDENCE_FOR_AUTO_ACCEPT = 0.85


def validate_extraction(result: ExtractionResult) -> list[str]:
    """Returns a list of human-readable issues. Empty list means the
    extraction can be accepted automatically."""
    issues: list[str] = []

    if result.confidence_score < MIN_CONFIDENCE_FOR_AUTO_ACCEPT:
        issues.append(
            f"confidence {result.confidence_score:.2f} below "
            f"{MIN_CONFIDENCE_FOR_AUTO_ACCEPT} threshold"
        )

    if not result.vendor_name:
        issues.append("vendor_name missing")

    if not result.invoice_number:
        issues.append("invoice_number missing")

    if result.line_items and result.subtotal is not None:
        line_items_sum = sum((item.amount for item in result.line_items), Decimal("0"))
        if abs(line_items_sum - result.subtotal) > AMOUNT_TOLERANCE:
            issues.append(
                f"line items sum to {line_items_sum} but subtotal is {result.subtotal}"
            )

    if result.subtotal is not None and result.tax is not None and result.total is not None:
        expected_total = result.subtotal + result.tax
        if abs(expected_total - result.total) > AMOUNT_TOLERANCE:
            issues.append(
                f"subtotal + tax = {expected_total} but total is {result.total}"
            )

    return issues
