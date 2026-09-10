from __future__ import annotations

import os
from dataclasses import dataclass


try:
    import yaml
except Exception:  # pragma: no cover - YAML optional for tests
    yaml = None


def _load_yaml(path: str) -> dict:
    if not yaml or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class Config:
    STRATUS_BUCKET: str | None = None
    WORKER_APPSAIL_ID: str | None = None
    DATABASE_URL: str | None = None


def load_config() -> Config:
    # Layered load: application.yaml -> local_application.yaml -> env
    base = _load_yaml("application.yaml")
    local = _load_yaml("local_application.yaml")

    merged = {**(base or {}), **(local or {})}

    # flatten expected keys
    bucket = merged.get("stratus", {}).get("bucket")
    worker_id = merged.get("worker", {}).get("appsail_id")
    db_url = merged.get("database", {}).get("url")

    # override from env if present
    bucket = os.getenv("STRATUS_BUCKET", bucket)
    worker_id = os.getenv("WORKER_APPSAIL_ID", worker_id)
    db_url = os.getenv("DATABASE_URL", db_url)

    return Config(STRATUS_BUCKET=bucket, WORKER_APPSAIL_ID=worker_id, DATABASE_URL=db_url)


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config
