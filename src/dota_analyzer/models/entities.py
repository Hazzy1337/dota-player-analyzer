from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Player:
    account_id: int
    name: str | None = None
    avatar_url: str | None = None
    rank_tier: int | None = None
    leaderboard_rank: int | None = None
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Match:
    match_id: int
    start_time: int
    date: datetime
    duration: int | None = None
    game_mode: int | str | None = None
    lobby_type: int | str | None = None
    ranked: bool | None = None
    turbo: bool | None = None
    hero_id: int | None = None
    hero_name: str | None = None
    role: str | None = None
    lane: str | None = None
    radiant_or_dire: str | None = None
    win: bool | None = None
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    last_hits: int | None = None
    denies: int | None = None
    gpm: int | None = None
    xpm: int | None = None
    hero_damage: int | None = None
    tower_damage: int | None = None
    hero_healing: int | None = None
    net_worth: int | None = None
    level: int | None = None
    party_size: int | None = None
    party_players: list[int] | None = None
    rank_change: int | None = None
    mmr_change: int | None = None
    double_down_multiplier: int | None = None
    items: list[int] | None = None
    item_timings: dict[str, float] | None = None
    neutral_item: int | None = None
    aghanims: bool | None = None
    shard: bool | None = None
    lane_result: str | None = None
    first_10_min_networth: int | None = None
    networth_15: int | None = None
    networth_20: int | None = None
    networth_25: int | None = None
    networth_30: int | None = None
    kill_participation: float | None = None
    wards_placed: int | None = None
    wards_destroyed: int | None = None
    camps_stacked: int | None = None
    runes: int | None = None
    buybacks: int | None = None
    roshan_participation: int | None = None
    tower_participation: int | None = None
    objective_events: list[dict[str, Any]] | None = None
    death_timestamps: list[int] | None = None
    kill_timestamps: list[int] | None = None
    assists_timestamps: list[int] | None = None
    source: str = "unknown"
    enriched: bool = False
    inferred_fields: list[str] = field(default_factory=list)

    @property
    def loss(self) -> bool | None:
        return None if self.win is None else not self.win

    @property
    def kda(self) -> float | None:
        if self.kills is None or self.deaths is None or self.assists is None:
            return None
        return (self.kills + self.assists) / max(1, self.deaths)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["date"] = self.date.isoformat()
        value["loss"] = self.loss
        value["kda"] = self.kda
        return value
