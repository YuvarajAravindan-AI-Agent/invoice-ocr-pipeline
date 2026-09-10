from __future__ import annotations

import os
from pathlib import Path


class LocalObjectStore:
    """Simple local filesystem object store used for local compose/tests.

    Stores objects under `/tmp/invoice-objects` using the object key path.
    This is intentionally minimal and not meant for production.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self._base = Path(base_dir or os.getenv("LOCAL_OBJECT_STORE_DIR", "/tmp/invoice-objects"))
        self._base.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        dest = self._base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)

    def get(self, key: str) -> bytes:
        p = self._base / key
        with open(p, "rb") as fh:
            return fh.read()
