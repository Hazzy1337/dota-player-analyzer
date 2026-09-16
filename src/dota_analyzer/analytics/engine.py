from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np

from ..models import Match
from .sessions import split_sessions


def _numbers(values: Iterable[float | int | None]) -> list[float]:
    return [float(value) for value in values if value is not None and not math.isnan(float(value))]


def _mean(values: Iterable[float | int | None]) -> float | None:
    clean = _numbers(values)
    return round(statistics.fmean(clean), 2) if clean else None


def _median(values: Iterable[float | int | None]) -> float | None:
    clean = _numbers(values)
    return round(statistics.median(clean), 2) if clean else None


def _wr(matches: Iterable[Match]) -> float | None:
    known = [match.win for match in matches if match.win is not None]
    return round(sum(known) / len(known) * 100, 2) if known else None


def _confidence(n: int) -> str:
    if n >= 20:
        return "high"
    if n >= 10:
        return "medium"
    if n >= 5:
        return "low"
    return "insufficient"


def _group(matches: list[Match], key) -> list[dict[str, Any]]:
    groups: dict[str, list[Match]] = defaultdict(list)
    for match in matches:
        value = key(match)
        groups[str(value if value is not None else "Not available")].append(match)
    result = []
    for name, rows in groups.items():
        result.append(
            {
                "name": name,
                "matches": len(rows),
                "wins": sum(match.win is True for match in rows),
                "losses": sum(match.win is False for match in rows),
                "winrate": _wr(rows),
                "kda": _mean(match.kda for match in rows),
                "deaths": _mean(match.deaths for match in rows),
                "gpm": _mean(match.gpm for match in rows),
                "xpm": _mean(match.xpm for match in rows),
                "confidence": _confidence(len(rows)),
            }
        )
    return sorted(result, key=lambda item: item["matches"], reverse=True)


def _death_buckets(matches: list[Match]) -> list[dict[str, Any]]:
    buckets = [("0–3", 0, 3), ("4–5", 4, 5), ("6–7", 6, 7), ("8–9", 8, 9), ("10+", 10, 10_000)]
    result = []
    for label, low, high in buckets:
        rows = [match for match in matches if match.deaths is not None and low <= match.deaths <= high]
        result.append({"name": label, "matches": len(rows), "winrate": _wr(rows), "confidence": _confidence(len(rows))})
    return result


def _sessions(matches: list[Match]) -> dict[str, Any]:
    sessions = split_sessions(matches)
    position: dict[str, list[Match]] = defaultdict(list)
    for session in sessions:
        for index, match in enumerate(session.matches, start=1):
            position[str(index if index <= 5 else "6+")].append(match)
    position_rows = [
        {"game": key, "matches": len(rows), "winrate": _wr(rows), "confidence": _confidence(len(rows))}
        for key, rows in sorted(position.items(), key=lambda item: (item[0] == "6+", item[0]))
    ]
    early = [match for session in sessions for match in session.matches[:3]]
    late = [match for session in sessions for match in session.matches[5:]]
    return {
        "count": len(sessions),
        "average_length": _mean(len(session.matches) for session in sessions),
        "longest": max((len(session.matches) for session in sessions), default=0),
        "by_game_number": position_rows,
        "first_3_wr": _wr(early),
        "game_6_plus_wr": _wr(late),
        "fatigue_delta": round((_wr(late) or 0) - (_wr(early) or 0), 2) if late and early else None,
    }


def _streaks(matches: list[Match]) -> dict[str, Any]:
    outcomes = [match.win for match in sorted(matches, key=lambda item: item.start_time) if match.win is not None]
    runs: list[tuple[bool, int]] = []
    for outcome in outcomes:
        if runs and runs[-1][0] == outcome:
            runs[-1] = (outcome, runs[-1][1] + 1)
        else:
            runs.append((outcome, 1))
    after: dict[str, dict[str, Any]] = {}
    for target in (True, False):
        label = "win" if target else "loss"
        for count in (1, 2, 3):
            next_results: list[bool] = []
            for index in range(count, len(outcomes)):
                if all(outcomes[index - offset - 1] == target for offset in range(count)):
                    next_results.append(outcomes[index])
            after[f"after_{count}_{label}"] = {
                "matches": len(next_results),
                "winrate": round(sum(next_results) / len(next_results) * 100, 2) if next_results else None,
                "confidence": _confidence(len(next_results)),
            }
    return {
        "longest_win": max((length for won, length in runs if won), default=0),
        "longest_loss": max((length for won, length in runs if not won), default=0),
        "average_streak": _mean(length for _, length in runs),
        **after,
    }


def _trend(matches: list[Match]) -> dict[str, Any]:
    if not matches:
        return {"segments": [], "direction": "not_enough_data"}
    ordered = sorted(matches, key=lambda item: item.start_time)
    chunks = np.array_split(np.array(ordered, dtype=object), 3)
    segments = []
    for index, chunk in enumerate(chunks, start=1):
        rows = list(chunk)
        segments.append(
            {
                "segment": index,
                "matches": len(rows),
                "winrate": _wr(rows),
                "deaths": _mean(match.deaths for match in rows),
                "kda": _mean(match.kda for match in rows),
                "gpm": _mean(match.gpm for match in rows),
            }
        )
    winrates = [item["winrate"] for item in segments if item["winrate"] is not None]
    if len(winrates) < 3 or len(matches) < 15:
        direction = "not_enough_data"
    elif max(winrates) - min(winrates) >= 15 and not (winrates[0] <= winrates[1] <= winrates[2] or winrates[0] >= winrates[1] >= winrates[2]):
        direction = "volatile"
    elif winrates[-1] - winrates[0] >= 5:
        direction = "improving"
    elif winrates[0] - winrates[-1] >= 5:
        direction = "declining"
    else:
        direction = "stable"
    return {"segments": segments, "direction": direction}


def _consistency(matches: list[Match]) -> dict[str, Any]:
    fields = {name: _numbers(getattr(match, name) if name != "kda" else match.kda for match in matches) for name in ("kills", "deaths", "gpm", "xpm", "kda")}
    cvs = []
    variance = {}
    for name, values in fields.items():
        variance[name] = round(float(np.var(values)), 2) if len(values) >= 2 else None
        if len(values) >= 5 and np.mean(values):
            cvs.append(float(np.std(values) / abs(np.mean(values))))
    score = round(max(0.0, min(10.0, 10.0 - statistics.fmean(cvs) * 10)), 1) if cvs else None
    return {"score": score, "variance": variance, "confidence": _confidence(len(matches))}


def _score(value: float | None, explanation: str, evidence: list[str], sample: int, inferred: bool = True) -> dict[str, Any]:
    return {
        "score": round(max(0, min(10, value)), 1) if value is not None else None,
        "explanation": explanation if value is not None else "Not enough data.",
        "confidence": _confidence(sample),
        "evidence": evidence if value is not None else [],
        "estimated": inferred,
    }


def analyze_matches(matches: list[Match], timezone_name: str = "UTC") -> dict[str, Any]:
    known = [match for match in matches if match.win is not None]
    wins = sum(match.win is True for match in known)
    losses = sum(match.win is False for match in known)
    first = min((match.date for match in matches), default=None)
    last = max((match.date for match in matches), default=None)
    active_days = len({match.date.date() for match in matches})
    span_days = max(1, (last.date() - first.date()).days + 1) if first and last else 0
    overview = {
        "matches": len(matches),
        "wins": wins,
        "losses": losses,
        "unknown_results": len(matches) - len(known),
        "winrate": round(wins / len(known) * 100, 2) if known else None,
        "active_days": active_days,
        "days_without_dota": max(0, span_days - active_days),
        "average_matches_per_active_day": round(len(matches) / active_days, 2) if active_days else None,
        "average_duration_minutes": _mean((match.duration / 60) if match.duration else None for match in matches),
        "median_duration_minutes": _median((match.duration / 60) if match.duration else None for match in matches),
        "kills": _mean(match.kills for match in matches),
        "deaths": _mean(match.deaths for match in matches),
        "assists": _mean(match.assists for match in matches),
        "median_deaths": _median(match.deaths for match in matches),
        "kda": _mean(match.kda for match in matches),
        "gpm": _mean(match.gpm for match in matches),
        "xpm": _mean(match.xpm for match in matches),
        "last_hits": _mean(match.last_hits for match in matches),
        "hero_damage": _mean(match.hero_damage for match in matches),
        "tower_damage": _mean(match.tower_damage for match in matches),
        "kill_participation": _mean(match.kill_participation for match in matches),
        "from": first.isoformat() if first else None,
        "to": last.isoformat() if last else None,
    }
    heroes = _group(matches, lambda match: match.hero_name or match.hero_id)
    for hero in heroes:
        hero["pick_rate"] = round(hero["matches"] / len(matches) * 100, 2) if matches else None
    roles = _group([match for match in matches if match.role], lambda match: match.role)
    role_identity = round(max((item["matches"] for item in roles), default=0) / len(matches) * 10, 1) if matches and roles else None
    deaths_wins = _mean(match.deaths for match in matches if match.win is True)
    deaths_losses = _mean(match.deaths for match in matches if match.win is False)
    death_values = [(match.deaths, int(match.win)) for match in known if match.deaths is not None]
    death_corr = round(float(np.corrcoef([x[0] for x in death_values], [x[1] for x in death_values])[0, 1]), 3) if len(death_values) >= 5 and len(set(x[0] for x in death_values)) > 1 else None
    sessions = _sessions(matches)
    streaks = _streaks(matches)
    timezone_value = ZoneInfo(timezone_name)
    local_matches = [(match, match.date.astimezone(timezone_value)) for match in matches]
    time_of_day = _group(matches, lambda match: f"{(match.date.astimezone(timezone_value).hour // 4) * 4:02d}–{((match.date.astimezone(timezone_value).hour // 4 + 1) * 4):02d}")
    day_of_week = _group(matches, lambda match: match.date.astimezone(timezone_value).strftime("%A"))
    side = _group([match for match in matches if match.radiant_or_dire], lambda match: match.radiant_or_dire)
    duration = _group(
        [match for match in matches if match.duration],
        lambda match: "<25" if match.duration < 1500 else "25–35" if match.duration < 2100 else "35–45" if match.duration < 2700 else "45–55" if match.duration < 3300 else "55+",
    )
    weeks = _group(matches, lambda match: match.date.date() - timedelta(days=match.date.weekday()))
    trend = _trend(matches)
    consistency = _consistency(matches)
    party = _group([match for match in matches if match.party_size is not None], lambda match: "solo" if match.party_size in (0, 1) else f"party_{match.party_size}")
    role_main = roles[0]["name"] if roles else None
    archetype = "Not enough data"
    if overview["kda"] is not None and overview["deaths"] is not None:
        if overview["kills"] is not None and overview["kills"] >= 10 and overview["deaths"] >= 8:
            archetype = "Risk-heavy playmaker (inferred)"
        elif overview["gpm"] is not None and overview["gpm"] >= 550:
            archetype = "Farm-oriented core (inferred)"
        elif overview["deaths"] <= 6 and overview["assists"] is not None and overview["assists"] >= 12:
            archetype = "Stable team-oriented player (inferred)"
        else:
            archetype = "Balanced player (inferred)"
    evidence_count = len(matches)
    score_data = {
        "mechanics": _score(None, "", [], 0),
        "laning": _score(None, "", [], 0),
        "farming": _score((overview["gpm"] or 0) / 70 if overview["gpm"] is not None else None, "Estimated from period GPM; role-adjusted benchmark unavailable.", [f"Average GPM: {overview['gpm']}"] if overview["gpm"] is not None else [], evidence_count),
        "positioning": _score(max(0, 10 - (overview["deaths"] or 0) * 0.8) if overview["deaths"] is not None else None, "Estimated from deaths; replay positioning data is unavailable.", [f"Average deaths: {overview['deaths']}"] if overview["deaths"] is not None else [], evidence_count),
        "macro": _score(None, "", [], 0),
        "teamfight": _score(min(10, (overview["kda"] or 0) * 2) if overview["kda"] is not None else None, "Estimated from KDA; fight telemetry is incomplete.", [f"Period KDA: {overview['kda']}"] if overview["kda"] is not None else [], evidence_count),
        "objective_conversion": _score(None, "", [], 0),
        "hero_mastery": _score(min(10, max((hero["matches"] for hero in heroes), default=0) / max(1, len(matches)) * 15) if matches else None, "Estimated from hero concentration.", [f"Most-played hero share: {heroes[0]['pick_rate']}%"] if heroes else [], evidence_count),
        "role_specialization": _score(role_identity, "Estimated from known role distribution.", [f"Main known role: {role_main}"] if role_main else [], sum(item["matches"] for item in roles)),
        "consistency": _score(consistency["score"], "Computed from coefficient of variation for available performance fields.", [f"Consistency model: {consistency['score']}/10"] if consistency["score"] is not None else [], evidence_count),
        "discipline": _score(max(0, 10 - (overview["deaths"] or 0) * 0.75) if overview["deaths"] is not None else None, "Estimated from death rate only.", [f"Average deaths: {overview['deaths']}"] if overview["deaths"] is not None else [], evidence_count),
        "mental_stamina": _score(max(0, min(10, 5 + (sessions["fatigue_delta"] or 0) / 5)) if sessions["fatigue_delta"] is not None else None, "Estimated from game 6+ versus first-three session win rate.", [f"Session fatigue delta: {sessions['fatigue_delta']} pp"] if sessions["fatigue_delta"] is not None else [], sum(item["matches"] for item in sessions["by_game_number"])),
        "late_game_decision_making": _score(None, "", [], 0),
        "map_awareness": _score(None, "", [], 0),
    }
    return {
        "overview": overview,
        "heroes": heroes,
        "roles": {"rows": roles, "main_role": role_main, "identity_score": role_identity, "known_sample": sum(item["matches"] for item in roles)},
        "deaths": {"wins": deaths_wins, "losses": deaths_losses, "correlation_with_win": death_corr, "buckets": _death_buckets(matches)},
        "sessions": sessions,
        "streaks": streaks,
        "time_of_day": time_of_day,
        "day_of_week": day_of_week,
        "party": party,
        "side": side,
        "duration": duration,
        "weeks": sorted(weeks, key=lambda item: item["name"]),
        "consistency": consistency,
        "trend": trend,
        "archetype": archetype,
        "skill_scores": score_data,
        "unavailable": {
            "lead_conversion": not any(match.networth_20 is not None for match in matches),
            "objective_conversion": not any(match.objective_events for match in matches),
            "item_timings": not any(match.item_timings for match in matches),
            "late_game_deaths": not any(match.death_timestamps for match in matches),
        },
    }


def compare_analyses(analyses: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for analysis in analyses:
        overview = analysis["overview"]
        rows.append(
            {
                "player": analysis["player"],
                "matches": overview["matches"],
                "winrate": overview["winrate"],
                "kda": overview["kda"],
                "deaths": overview["deaths"],
                "gpm": overview["gpm"],
                "xpm": overview["xpm"],
                "main_role": analysis["roles"]["main_role"],
                "role_known_sample": analysis["roles"]["known_sample"],
                "hero_pool": len(analysis["heroes"]),
                "consistency": analysis["consistency"]["score"],
                "session_fatigue_delta": analysis["sessions"]["fatigue_delta"],
                "archetype": analysis["archetype"],
                "data_quality": analysis["data_quality"],
            }
        )
    return {
        "players": rows,
        "note": "Metrics are descriptive and role/sample dependent; no overall 'better player' claim is made.",
    }
