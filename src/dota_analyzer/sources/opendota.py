from __future__ import annotations

from typing import Any

from ..cache import CacheManager
from ..config import Settings
from .base import BaseClient


class OpenDotaClient(BaseClient):
    base_url = "https://api.opendota.com/api"

    def _json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        params = dict(params or {})
        if self.settings.opendota_api_key:
            params["api_key"] = self.settings.opendota_api_key
        url = f"{self.base_url}{path}"
        cache_key = f"{url}?{sorted(params.items())}"
        cached = self.cache.get_json("opendota", cache_key)
        if cached is not None:
            return cached
        data = self._request(url, params=params).json()
        self.cache.set_json("opendota", cache_key, data)
        return data

    def get_profile(self, account_id: int) -> dict[str, Any]:
        return self._json(f"/players/{account_id}")

    def get_matches(self, account_id: int, *, days: int | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if days is not None:
            params["date"] = days
        if limit is not None:
            params["limit"] = limit
        value = self._json(f"/players/{account_id}/matches", params)
        return value if isinstance(value, list) else []

    def get_match(self, match_id: int) -> dict[str, Any]:
        value = self._json(f"/matches/{match_id}")
        return value if isinstance(value, dict) else {}

    def get_heroes(self) -> dict[int, str]:
        value = self._json("/constants/heroes")
        return {
            int(key): str(hero.get("localized_name") or hero.get("name") or key)
            for key, hero in value.items()
        }

