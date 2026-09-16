from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Match, Player


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def normalize_profile(account_id: int, raw: dict[str, Any], source: str) -> Player:
    profile = raw.get("profile") if isinstance(raw.get("profile"), dict) else raw
    return Player(
        account_id=account_id,
        name=profile.get("personaname") or profile.get("name") or f"Player {account_id}",
        avatar_url=profile.get("avatarfull") or profile.get("avatar_url"),
        rank_tier=_as_int(raw.get("rank_tier")),
        leaderboard_rank=_as_int(raw.get("leaderboard_rank")),
        source=source,
    )


def _player_from_detail(detail: dict[str, Any], account_id: int) -> dict[str, Any]:
    for player in detail.get("players") or []:
        if _as_int(player.get("account_id")) == account_id:
            return player
    return {}


def normalize_match(
    raw: dict[str, Any],
    account_id: int,
    heroes: dict[int, str],
    detail: dict[str, Any] | None = None,
) -> Match:
    detail = detail or {}
    player = _player_from_detail(detail, account_id)
    merged = dict(raw)
    merged.update({key: value for key, value in player.items() if value is not None})
    start_time = _as_int(merged.get("start_time")) or 0
    player_slot = _as_int(merged.get("player_slot"))
    radiant = player_slot is not None and player_slot < 128
    radiant_win = merged.get("radiant_win")
    win = merged.get("win")
    if win is None and radiant_win is not None and player_slot is not None:
        win = bool(radiant_win) == radiant
    hero_id = _as_int(merged.get("hero_id"))
    lane_role = _as_int(merged.get("lane_role"))
    lane = {1: "safe", 2: "mid", 3: "off", 4: "jungle"}.get(lane_role)
    role = merged.get("role")
    inferred: list[str] = []
    if not role and lane == "mid":
        role = "Pos 2"
        inferred.append("role")
    elif not role and lane == "off":
        role = "Pos 3"
        inferred.append("role")
    item_ids = [_as_int(merged.get(f"item_{index}")) for index in range(6)]
    item_ids = [item for item in item_ids if item]
    kills_log = merged.get("kills_log") or []
    objectives = detail.get("objectives") or None
    duration = _as_int(merged.get("duration") or detail.get("duration"))
    return Match(
        match_id=int(merged["match_id"]),
        start_time=start_time,
        date=datetime.fromtimestamp(start_time, tz=timezone.utc),
        duration=duration,
        game_mode=merged.get("game_mode"),
        lobby_type=merged.get("lobby_type"),
        ranked=(merged.get("lobby_type") == 7) if merged.get("lobby_type") is not None else merged.get("ranked"),
        turbo=(merged.get("game_mode") == 23) if merged.get("game_mode") is not None else merged.get("turbo"),
        hero_id=hero_id,
        hero_name=merged.get("hero_name") or heroes.get(hero_id),
        role=role,
        lane=lane,
        radiant_or_dire=("Radiant" if radiant else "Dire") if player_slot is not None else None,
        win=bool(win) if win is not None else None,
        kills=_as_int(merged.get("kills")),
        deaths=_as_int(merged.get("deaths")),
        assists=_as_int(merged.get("assists")),
        last_hits=_as_int(merged.get("last_hits")),
        denies=_as_int(merged.get("denies")),
        gpm=_as_int(merged.get("gold_per_min")),
        xpm=_as_int(merged.get("xp_per_min")),
        hero_damage=_as_int(merged.get("hero_damage")),
        tower_damage=_as_int(merged.get("tower_damage")),
        hero_healing=_as_int(merged.get("hero_healing")),
        net_worth=_as_int(merged.get("net_worth") or merged.get("total_gold")),
        level=_as_int(merged.get("level")),
        party_size=_as_int(merged.get("party_size")),
        party_players=None,
        rank_change=_as_int(merged.get("rank_change")),
        mmr_change=_as_int(merged.get("mmr_change")),
        double_down_multiplier=_as_int(merged.get("double_rank")),
        items=item_ids or None,
        neutral_item=_as_int(merged.get("item_neutral")),
        aghanims=bool(merged.get("aghanims_scepter")) if merged.get("aghanims_scepter") is not None else None,
        shard=bool(merged.get("aghanims_shard")) if merged.get("aghanims_shard") is not None else None,
        kill_participation=float(merged["kill_participation"]) if merged.get("kill_participation") is not None else None,
        wards_placed=_as_int(merged.get("obs_placed")),
        wards_destroyed=_as_int(merged.get("observer_kills")),
        camps_stacked=_as_int(merged.get("camps_stacked")),
        runes=_as_int(merged.get("rune_pickups")),
        buybacks=_as_int(merged.get("buyback_count")),
        objective_events=objectives,
        death_timestamps=[int(item["time"]) for item in merged.get("deaths_log") or [] if "time" in item] or None,
        kill_timestamps=[int(item["time"]) for item in kills_log if "time" in item] or None,
        source=str(raw.get("source") or "opendota"),
        enriched=bool(detail),
        inferred_fields=inferred,
    )

