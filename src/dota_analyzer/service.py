from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .analytics.engine import analyze_matches, compare_analyses
from .cache import CacheManager
from .config import Settings
from .models import Match, Player
from .normalization import normalize_match, normalize_profile
from .recommendations.engine import build_recommendations
from .reporting.pdf import render_comparison_pdf, render_player_pdf
from .sources.base import SourceError
from .sources.dotabuff import DotabuffClient
from .sources.opendota import OpenDotaClient
from .utils.ids import normalize_player_id

LOG = logging.getLogger(__name__)


class AnalyzerService:
    def __init__(self, settings: Settings, *, use_cache: bool = True, save_raw: bool = False):
        settings.ensure_directories()
        self.settings = settings
        self.cache = CacheManager(settings.cache_dir, settings.cache_ttl_hours, use_cache)
        self.dotabuff = DotabuffClient(settings, self.cache, save_raw=save_raw)
        self.opendota = OpenDotaClient(settings, self.cache)

    def close(self) -> None:
        self.dotabuff.close()
        self.opendota.close()

    def _acquire(
        self,
        account_id: int,
        *,
        days: int | None,
        matches_limit: int | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> tuple[Player, list[Match], dict[str, Any]]:
        now = datetime.now(timezone.utc)
        end = to_date or now
        start = from_date or (end - timedelta(days=days or 45) if matches_limit is None else None)
        raw_matches: list[dict[str, Any]] = []
        profile_raw: dict[str, Any] = {}
        primary_source = "dotabuff"
        warnings: list[str] = []
        try:
            profile_raw = self.dotabuff.get_profile(account_id)
            raw_matches = self.dotabuff.get_matches(
                account_id,
                start_timestamp=int(start.timestamp()) if start else None,
                end_timestamp=int(end.timestamp()),
                limit=matches_limit,
            )
        except SourceError as exc:
            primary_source = "opendota"
            warnings.append(f"Dotabuff unavailable: {exc}")
            LOG.warning("Dotabuff unavailable; using OpenDota: %s", exc)
            profile_raw = self.opendota.get_profile(account_id)
            od_days = days
            if from_date:
                od_days = max(1, (end - from_date).days + 1)
            raw_matches = self.opendota.get_matches(account_id, days=od_days, limit=matches_limit)

        heroes = self.opendota.get_heroes()
        player = normalize_profile(account_id, profile_raw, primary_source)
        normalized: list[Match] = []
        enrichment_enabled = self.settings.enrich_limit > 0
        for index, raw in enumerate(raw_matches):
            timestamp = int(raw.get("start_time") or 0)
            if start and timestamp < int(start.timestamp()):
                continue
            if end and timestamp > int(end.timestamp()):
                continue
            detail: dict[str, Any] | None = None
            if enrichment_enabled and index < self.settings.enrich_limit:
                try:
                    detail = self.opendota.get_match(int(raw["match_id"]))
                except SourceError as exc:
                    warnings.append(f"OpenDota match enrichment stopped: {exc}")
                    enrichment_enabled = False
            normalized.append(normalize_match(raw, account_id, heroes, detail))
            if matches_limit and len(normalized) >= matches_limit:
                break
        normalized.sort(key=lambda match: match.start_time)
        quality = {
            "primary_source": primary_source,
            "dotabuff_matches": len(normalized) if primary_source == "dotabuff" else 0,
            "opendota_matches": len(normalized) if primary_source == "opendota" else 0,
            "opendota_enriched": sum(match.enriched for match in normalized),
            "missing_detailed_telemetry": sum(not match.enriched for match in normalized),
            "warnings": list(dict.fromkeys(warnings)),
        }
        quality["confidence"] = "high" if len(normalized) >= 50 else "medium" if len(normalized) >= 20 else "low"
        return player, normalized, quality

    def analyze(
        self,
        player_input: str,
        *,
        days: int | None = 45,
        matches_limit: int | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        language: str = "ru",
        compare_with_previous: bool = False,
    ) -> dict[str, Any]:
        account_id = normalize_player_id(player_input)
        if matches_limit is not None and days == 45 and from_date is None:
            days = None
        player, matches, quality = self._acquire(
            account_id,
            days=days,
            matches_limit=matches_limit,
            from_date=from_date,
            to_date=to_date,
        )
        analysis = analyze_matches(matches, timezone_name=self.settings.timezone)
        recommendations = build_recommendations(analysis, language=language)
        analysis.update(recommendations)
        analysis["player"] = player.to_dict()
        analysis["period"] = {
            "mode": "matches" if matches_limit is not None else "days",
            "days": days,
            "matches_requested": matches_limit,
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
        }
        analysis["data_quality"] = quality
        output = self.settings.output_dir / str(account_id)
        output.mkdir(parents=True, exist_ok=True)
        previous_path = output / "analysis.json"
        previous = None
        if compare_with_previous and previous_path.exists():
            try:
                previous = json.loads(previous_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                previous = None
        if compare_with_previous:
            if previous:
                old_overview = previous.get("overview", {})
                analysis["compare_with_previous"] = {
                    "available": True,
                    "previous_period": previous.get("period"),
                    "winrate_change_pp": _difference(overview=analysis["overview"], previous=old_overview, key="winrate"),
                    "deaths_change": _difference(overview=analysis["overview"], previous=old_overview, key="deaths"),
                    "hero_pool_change": len(analysis["heroes"]) - len(previous.get("heroes", [])),
                    "role_change": f"{previous.get('roles', {}).get('main_role')} → {analysis['roles']['main_role']}",
                    "session_fatigue_change": _difference(overview=analysis["sessions"], previous=previous.get("sessions", {}), key="fatigue_delta"),
                }
            else:
                analysis["compare_with_previous"] = {"available": False, "reason": "No previous analysis.json was found."}
        (output / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        pd.DataFrame([match.to_dict() for match in matches]).to_csv(output / "matches.csv", index=False, encoding="utf-8-sig")
        report = render_player_pdf(player, analysis, output, language=language)
        analysis["files"] = {
            "analysis_json": str(output / "analysis.json"),
            "matches_csv": str(output / "matches.csv"),
            "report_pdf": str(report),
        }
        (output / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        return analysis

    def compare(self, player_inputs: list[str], **kwargs: Any) -> dict[str, Any]:
        analyses = [self.analyze(item, **kwargs) for item in player_inputs]
        comparison = compare_analyses(analyses)
        output = self.settings.output_dir / "comparison"
        output.mkdir(parents=True, exist_ok=True)
        (output / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
        report = render_comparison_pdf(comparison, output, language=kwargs.get("language", "ru"))
        comparison["files"] = {"comparison_json": str(output / "comparison.json"), "report_pdf": str(report)}
        return comparison


def _difference(*, overview: dict[str, Any], previous: dict[str, Any], key: str) -> float | None:
    current_value = overview.get(key)
    previous_value = previous.get(key)
    if current_value is None or previous_value is None:
        return None
    return round(float(current_value) - float(previous_value), 2)
