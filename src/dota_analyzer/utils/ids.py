from __future__ import annotations

import re

STEAM64_OFFSET = 76561197960265728


def normalize_player_id(value: str | int) -> int:
    """Return a Steam32/Dota account id from an id or supported profile URL."""
    text = str(value).strip()
    url_match = re.search(
        r"(?:dotabuff\.com/players|opendota\.com/players)/([0-9]{1,20})(?:[/?#]|$)",
        text,
        re.IGNORECASE,
    )
    if url_match:
        text = url_match.group(1)
    if not re.fullmatch(r"[0-9]{1,20}", text):
        raise ValueError(f"Unsupported player identifier: {value!r}")
    number = int(text)
    if number >= STEAM64_OFFSET:
        number -= STEAM64_OFFSET
    if number <= 0 or number > 0xFFFFFFFF:
        raise ValueError(f"Player id is outside the Steam32 range: {value!r}")
    return number


def account_id_to_steam64(account_id: int) -> int:
    return normalize_player_id(account_id) + STEAM64_OFFSET

