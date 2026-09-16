from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from dota_analyzer.models import Match


@pytest.fixture
def sample_matches() -> list[Match]:
    start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    matches: list[Match] = []
    for index in range(30):
        date = start + timedelta(hours=index * 3)
        matches.append(
            Match(
                match_id=8000000000 + index,
                start_time=int(date.timestamp()),
                date=date,
                duration=1800 + index * 10,
                hero_id=1 if index < 18 else 2,
                hero_name="Anti-Mage" if index < 18 else "Axe",
                role="Pos 1" if index < 20 else "Pos 3",
                lane="safe" if index < 20 else "off",
                radiant_or_dire="Radiant" if index % 2 == 0 else "Dire",
                win=index % 3 != 0,
                kills=7 + index % 5,
                deaths=4 + index % 8,
                assists=10 + index % 7,
                last_hits=180 + index,
                gpm=500 + index,
                xpm=600 + index,
                hero_damage=20000 + index * 100,
                tower_damage=2000 + index * 20,
                party_size=1 if index % 2 else 2,
                source="fixture",
            )
        )
    return matches

