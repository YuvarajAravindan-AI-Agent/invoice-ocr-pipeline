# domain

Business rules only. No cloud SDK imports, no provider-specific types,
no environment variables read directly here. If this layer needs
something from the outside world (storage, secrets, events, scheduling),
it depends on a port interface defined in `../application/`, never on a
concrete adapter.

- `entities.py` — `Invoice`, `LineItem`, `InvoiceStatus`
- `extraction.py` — `ExtractionResult`, the shape any OCR implementation must return
- `validation.py` — `validate_extraction()`, decides EXTRACTED vs. NEEDS_REVIEW

Tested in `../../tests/unit/test_validation.py`.
