from __future__ import annotations

from uuid import UUID


class NoopExtractionQueue:
    """A no-op extraction queue used in local tests: enqueue does nothing."""

    def enqueue(self, invoice_id: UUID) -> None:
        return None
