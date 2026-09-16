from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ..cache import CacheManager
from ..config import Settings

LOG = logging.getLogger(__name__)


class SourceError(RuntimeError):
    pass


class SourceBlocked(SourceError):
    pass


class BaseClient:
    def __init__(self, settings: Settings, cache: CacheManager):
        self.settings = settings
        self.cache = cache
        self.client = httpx.Client(
            timeout=settings.timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": settings.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            },
        )
        self._last_request = 0.0

    def close(self) -> None:
        self.client.close()

    def _wait_rate_limit(self) -> None:
        remaining = self.settings.rate_limit_seconds - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)

    def _request(self, url: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        error: Exception | None = None
        for attempt in range(self.settings.retries):
            self._wait_rate_limit()
            try:
                response = self.client.get(url, params=params)
                self._last_request = time.monotonic()
                LOG.info("GET %s status=%s attempt=%s", response.url, response.status_code, attempt + 1)
                if response.status_code in {403, 429}:
                    if response.status_code == 403:
                        raise SourceBlocked(f"Source blocked HTTP access: {response.url}")
                    raise SourceError(f"Rate limited by source: {response.url}")
                response.raise_for_status()
                return response
            except SourceBlocked:
                raise
            except (httpx.HTTPError, SourceError) as exc:
                error = exc
                if attempt + 1 < self.settings.retries:
                    delay = min(8.0, 0.75 * (2**attempt))
                    LOG.warning("Request failed: %s; retry in %.2fs", exc, delay)
                    time.sleep(delay)
        raise SourceError(str(error) if error else f"Request failed: {url}")

