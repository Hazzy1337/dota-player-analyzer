from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..cache import CacheManager
from ..config import Settings
from .base import BaseClient, SourceBlocked, SourceError

LOG = logging.getLogger(__name__)


class DotabuffClient(BaseClient):
    base_url = "https://www.dotabuff.com"

    def __init__(self, settings: Settings, cache: CacheManager, save_raw: bool = False):
        super().__init__(settings, cache)
        self.save_raw = save_raw

    def _html(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        cached = self.cache.get_text("dotabuff", url)
        if cached is not None:
            return cached
        try:
            response = self._request(url)
            text = response.text
        except SourceBlocked:
            if not self.settings.browser_fallback:
                raise
            text = self._playwright_html(url)
        if "cf-chl-" in text or "Just a moment" in text:
            raise SourceError("Dotabuff returned a Cloudflare challenge")
        saved = self.cache.set_text("dotabuff", url, text)
        if self.save_raw:
            LOG.info("Saved raw Dotabuff HTML: %s", saved)
        return text

    def _playwright_html(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise SourceError("Dotabuff blocked HTTP and optional Playwright is not installed") from exc
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page(user_agent=self.settings.user_agent, locale="en-US")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=int(self.settings.timeout_seconds * 1000))
                page.wait_for_selector("table, h1", timeout=int(self.settings.timeout_seconds * 1000))
                return page.content()
            except Exception as exc:
                raise SourceError(f"Playwright fallback could not load Dotabuff: {exc}") from exc
            finally:
                browser.close()

    @staticmethod
    def parse_profile(html: str, account_id: int) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        title = soup.select_one("h1") or soup.select_one(".header-content-title")
        name = title.get_text(" ", strip=True) if title else None
        if name:
            name = re.sub(r"\s*Overview\s*$", "", name, flags=re.IGNORECASE).strip()
        image = soup.select_one(".image-player img, img.player-avatar, header img")
        return {
            "account_id": account_id,
            "name": name or f"Player {account_id}",
            "avatar_url": image.get("src") if isinstance(image, Tag) else None,
            "source": "dotabuff",
        }

    @staticmethod
    def _timestamp(row: Tag) -> int | None:
        time_node = row.select_one("time, [data-time], abbr[title]")
        if not time_node:
            return None
        raw = time_node.get("data-time") or time_node.get("datetime") or time_node.get("title")
        if raw and str(raw).isdigit():
            return int(raw)
        if raw:
            try:
                return int(datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp())
            except ValueError:
                pass
        return None

    @classmethod
    def parse_matches(cls, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        result: list[dict[str, Any]] = []
        for row in soup.select("table tbody tr"):
            match_link = row.select_one('a[href*="/matches/"]')
            if not match_link:
                continue
            id_match = re.search(r"/matches/(\d+)", str(match_link.get("href", "")))
            timestamp = cls._timestamp(row)
            if not id_match or timestamp is None:
                continue
            hero_link = row.select_one('a[href*="/heroes/"]')
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            row_text = " ".join(cells)
            won = bool(re.search(r"\bWon\b|\bПобеда\b", row_text, re.IGNORECASE))
            lost = bool(re.search(r"\bLost\b|\bПоражение\b", row_text, re.IGNORECASE))
            kda_match = re.search(r"\b(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\b", row_text)
            duration_match = re.search(r"\b(\d{1,2}):(\d{2})\b", row_text)
            result.append(
                {
                    "match_id": int(id_match.group(1)),
                    "start_time": timestamp,
                    "hero_name": hero_link.get_text(" ", strip=True) if hero_link else None,
                    "win": won if won or lost else None,
                    "kills": int(kda_match.group(1)) if kda_match else None,
                    "deaths": int(kda_match.group(2)) if kda_match else None,
                    "assists": int(kda_match.group(3)) if kda_match else None,
                    "duration": (int(duration_match.group(1)) * 60 + int(duration_match.group(2)))
                    if duration_match
                    else None,
                    "source": "dotabuff",
                }
            )
        return result

    def get_profile(self, account_id: int) -> dict[str, Any]:
        return self.parse_profile(self._html(f"/players/{account_id}"), account_id)

    def get_heroes_html(self, account_id: int) -> str:
        return self._html(f"/players/{account_id}/heroes")

    def get_activity_html(self, account_id: int) -> str:
        return self._html(f"/players/{account_id}/activity")

    def get_matches(
        self,
        account_id: int,
        *,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        seen: set[int] = set()
        for page in range(1, self.settings.max_pages + 1):
            rows = self.parse_matches(self._html(f"/players/{account_id}/matches?page={page}"))
            if not rows:
                break
            oldest = min(row["start_time"] for row in rows)
            for row in rows:
                if row["match_id"] in seen:
                    continue
                seen.add(row["match_id"])
                if end_timestamp and row["start_time"] > end_timestamp:
                    continue
                if start_timestamp and row["start_time"] < start_timestamp:
                    continue
                collected.append(row)
                if limit and len(collected) >= limit:
                    return sorted(collected, key=lambda item: item["start_time"], reverse=True)
            if start_timestamp and oldest < start_timestamp:
                break
        else:
            raise SourceError(f"Dotabuff pagination safety limit reached ({self.settings.max_pages})")
        return sorted(collected, key=lambda item: item["start_time"], reverse=True)
