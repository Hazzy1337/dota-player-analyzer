from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    cache_dir: Path = Path("cache")
    output_dir: Path = Path("output")
    cache_ttl_hours: int = int(os.getenv("DOTA_ANALYZER_CACHE_TTL_HOURS", "24"))
    timeout_seconds: float = 25.0
    retries: int = 3
    rate_limit_seconds: float = 1.1
    max_pages: int = 100
    timezone: str = os.getenv("DOTA_ANALYZER_TIMEZONE", "Europe/Berlin")
    opendota_api_key: str | None = os.getenv("OPENDOTA_API_KEY") or None
    steam_api_key: str | None = os.getenv("STEAM_WEB_API_KEY") or None
    enrich_limit: int = 20
    browser_fallback: bool = False
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/138 Safari/537.36"
    )

    def ensure_directories(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
