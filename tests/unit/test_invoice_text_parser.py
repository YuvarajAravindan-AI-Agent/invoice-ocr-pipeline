from decimal import Decimal

from app.adapters.catalyst._invoice_text_parser import parse_invoice_text

SAMPLE_OCR_TEXT = """Acme Corp
123 Business Rd

Invoice Number: INV-2026-001
Date: 2026-09-01

Widget A    2   50.00   100.00

Subtotal: $100.00
Tax: $18.00
Total: $118.00
"""


def test_parses_vendor_name_from_first_line():
    fields = parse_invoice_text(SAMPLE_OCR_TEXT)
    assert fields["vendor_name"] == "Acme Corp"


def test_parses_invoice_number():
    fields = parse_invoice_text(SAMPLE_OCR_TEXT)
    assert fields["invoice_number"] == "INV-2026-001"


def test_parses_amounts():
    fields = parse_invoice_text(SAMPLE_OCR_TEXT)
    assert fields["subtotal"] == Decimal("100.00")
    assert fields["tax"] == Decimal("18.00")
    assert fields["total"] == Decimal("118.00")


def test_total_regex_does_not_match_subtotal_line():
    """Regression guard: `total` and `subtotal` share the substring
    "total", so the total regex must not double-match the subtotal
    line — see the negative lookbehind in _invoice_text_parser.py."""
    fields = parse_invoice_text("Subtotal: $50.00\nTotal: $59.00\n")
    assert fields["subtotal"] == Decimal("50.00")
    assert fields["total"] == Decimal("59.00")


def test_missing_fields_are_none():
    fields = parse_invoice_text("just some random text with no invoice fields")
    assert fields["invoice_number"] is None
    assert fields["subtotal"] is None
    assert fields["tax"] is None
    assert fields["total"] is None
