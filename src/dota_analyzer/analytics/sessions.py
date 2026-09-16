from __future__ import annotations

from dataclasses import dataclass

from ..models import Match


@dataclass(slots=True)
class Session:
    matches: list[Match]


def split_sessions(matches: list[Match], gap_minutes: int = 90) -> list[Session]:
    if not matches:
        return []
    ordered = sorted(matches, key=lambda item: item.start_time)
    sessions: list[Session] = [Session([ordered[0]])]
    for match in ordered[1:]:
        previous = sessions[-1].matches[-1]
        previous_end = previous.start_time + (previous.duration or 0)
        if match.start_time - previous_end < gap_minutes * 60:
            sessions[-1].matches.append(match)
        else:
            sessions.append(Session([match]))
    return sessions

