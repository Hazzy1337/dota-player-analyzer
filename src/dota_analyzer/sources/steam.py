from __future__ import annotations

from typing import Any

from ..cache import CacheManager
from ..config import Settings
from ..utils.ids import account_id_to_steam64
from .base import BaseClient, SourceError


class SteamClient(BaseClient):
    endpoint = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"

    def __init__(self, settings: Settings, cache: CacheManager):
        super().__init__(settings, cache)
        if not settings.steam_api_key:
            raise SourceError("STEAM_WEB_API_KEY is not configured")

    def get_profile(self, account_id: int) -> dict[str, Any] | None:
        response = self._request(
            self.endpoint,
            params={"key": self.settings.steam_api_key, "steamids": account_id_to_steam64(account_id)},
        ).json()
        players = response.get("response", {}).get("players", [])
        return players[0] if players else None
