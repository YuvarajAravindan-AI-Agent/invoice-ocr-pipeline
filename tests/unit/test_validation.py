from decimal import Decimal

from app.domain.extraction import ExtractionResult
from app.domain.entities import LineItem
from app.domain.validation import validate_extraction


def _clean_result(**overrides) -> ExtractionResult:
    defaults = dict(
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        invoice_date_iso="2026-09-01T00:00:00+00:00",
        currency="INR",
        subtotal=Decimal("100.00"),
        tax=Decimal("18.00"),
        total=Decimal("118.00"),
        confidence_score=0.95,
        line_items=[LineItem("Widget", Decimal("2"), Decimal("50.00"), Decimal("100.00"))],
    )
    defaults.update(overrides)
    return ExtractionResult(**defaults)


def test_clean_extraction_has_no_issues():
    assert validate_extraction(_clean_result()) == []


def test_low_confidence_is_flagged():
    issues = validate_extraction(_clean_result(confidence_score=0.5))
    assert any("confidence" in issue for issue in issues)


def test_missing_vendor_name_is_flagged():
    issues = validate_extraction(_clean_result(vendor_name=None))
    assert "vendor_name missing" in issues


def test_missing_invoice_number_is_flagged():
    issues = validate_extraction(_clean_result(invoice_number=None))
    assert "invoice_number missing" in issues


def test_line_items_not_matching_subtotal_is_flagged():
    result = _clean_result(
        line_items=[LineItem("Widget", Decimal("1"), Decimal("50.00"), Decimal("50.00"))]
    )
    issues = validate_extraction(result)
    assert any("line items sum" in issue for issue in issues)


def test_subtotal_plus_tax_not_matching_total_is_flagged():
    issues = validate_extraction(_clean_result(total=Decimal("999.00")))
    assert any("subtotal + tax" in issue for issue in issues)
