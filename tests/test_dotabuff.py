from pathlib import Path

from dota_analyzer.cache import CacheManager
from dota_analyzer.config import Settings
from dota_analyzer.sources.dotabuff import DotabuffClient


def test_match_parsing():
    html = Path("tests/fixtures/dotabuff_matches.html").read_text(encoding="utf-8")
    rows = DotabuffClient.parse_matches(html)
    assert len(rows) == 2
    assert rows[0]["match_id"] == 9000000001
    assert rows[0]["hero_name"] == "Pudge"
    assert rows[0]["win"] is True
    assert (rows[0]["kills"], rows[0]["deaths"], rows[0]["assists"]) == (12, 4, 18)
    assert rows[0]["duration"] == 42 * 60 + 15
    assert rows[1]["win"] is False


def test_pagination(tmp_path):
    html = Path("tests/fixtures/dotabuff_matches.html").read_text(encoding="utf-8")
    empty = "<html><table><tbody></tbody></table></html>"
    client = DotabuffClient(Settings(cache_dir=tmp_path), CacheManager(tmp_path))
    calls = []

    def fake_html(path):
        calls.append(path)
        return html if "page=1" in path else empty

    client._html = fake_html
    rows = client.get_matches(1, start_timestamp=1786800000)
    client.close()
    assert len(rows) == 2
    assert calls == ["/players/1/matches?page=1", "/players/1/matches?page=2"]


def test_date_filter_stops_at_boundary(tmp_path):
    html = Path("tests/fixtures/dotabuff_matches.html").read_text(encoding="utf-8")
    client = DotabuffClient(Settings(cache_dir=tmp_path), CacheManager(tmp_path))
    calls = []

    def fake_html(path):
        calls.append(path)
        return html

    client._html = fake_html
    rows = client.get_matches(1, start_timestamp=1786900000)
    client.close()
    assert [row["match_id"] for row in rows] == [9000000001]
    assert calls == ["/players/1/matches?page=1"]


def test_match_limit_stops_pagination(tmp_path):
    html = Path("tests/fixtures/dotabuff_matches.html").read_text(encoding="utf-8")
    client = DotabuffClient(Settings(cache_dir=tmp_path), CacheManager(tmp_path))
    client._html = lambda path: html
    rows = client.get_matches(1, limit=1)
    client.close()
    assert len(rows) == 1
