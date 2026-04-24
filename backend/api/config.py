from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    api_title: str
    api_version: str
    cors_origins: list[str]


def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or ["*"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        api_title=os.getenv("API_TITLE", "ResearchGen API"),
        api_version=os.getenv("API_VERSION", "0.1.0"),
        cors_origins=_parse_csv_env("CORS_ORIGINS", "*"),
    )
