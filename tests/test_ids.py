import pytest

from dota_analyzer.utils.ids import STEAM64_OFFSET, normalize_player_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("336235516", 336235516),
        (336235516, 336235516),
        (f"https://ru.dotabuff.com/players/336235516", 336235516),
        (f"https://www.opendota.com/players/336235516/matches", 336235516),
        (str(STEAM64_OFFSET + 336235516), 336235516),
    ],
)
def test_normalize_player_id(value, expected):
    assert normalize_player_id(value) == expected


def test_rejects_invalid_id():
    with pytest.raises(ValueError):
        normalize_player_id("not-a-player")

