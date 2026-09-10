from __future__ import annotations

import os
from dataclasses import asdict
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class StratusConfig(BaseModel):
    bucket: str = Field(..., min_length=1)


class WorkerConfig(BaseModel):
    appsail_id: Optional[str] = None


class DatabaseConfig(BaseModel):
    url: Optional[str] = None


class Settings(BaseModel):
    stratus: StratusConfig
    worker: WorkerConfig = WorkerConfig()
    database: DatabaseConfig = DatabaseConfig()


_config: Optional[Settings] = None


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(env: Optional[str] = None) -> Settings:
    """Load layered configuration:
    - application.yaml
    - application.{env}.yaml (if env provided or from APP_ENV)
    - local_application.yaml
    - environment variables override
    Validates the merged config against the `Settings` schema.
    """
    base = _load_yaml("application.yaml")
    if env is None:
        env = os.getenv("APP_ENV") or os.getenv("ENV") or "development"
    env_file = f"application.{env}.yaml"
    env_cfg = _load_yaml(env_file)
    local = _load_yaml("local_application.yaml")

    merged = {**(base or {}), **(env_cfg or {}), **(local or {})}

    # Apply environment overrides
    if os.getenv("STRATUS_BUCKET"):
        merged.setdefault("stratus", {})["bucket"] = os.getenv("STRATUS_BUCKET")
    if os.getenv("WORKER_APPSAIL_ID"):
        merged.setdefault("worker", {})["appsail_id"] = os.getenv("WORKER_APPSAIL_ID")
    if os.getenv("DATABASE_URL"):
        merged.setdefault("database", {})["url"] = os.getenv("DATABASE_URL")

    try:
        settings = Settings(**merged)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}") from exc

    return settings


def get_config() -> Settings:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def as_dict() -> dict:
    return asdict(get_config().dict())
