from dota_analyzer.analytics.engine import analyze_matches
from dota_analyzer.models import Player
from dota_analyzer.recommendations.engine import build_recommendations
from dota_analyzer.reporting.pdf import render_player_pdf


def test_pdf_generation(tmp_path, sample_matches):
    analysis = analyze_matches(sample_matches)
    analysis.update(build_recommendations(analysis))
    analysis["data_quality"] = {
        "primary_source": "fixture",
        "dotabuff_matches": 30,
        "opendota_matches": 0,
        "opendota_enriched": 0,
        "missing_detailed_telemetry": 30,
        "confidence": "medium",
        "warnings": [],
    }
    path = render_player_pdf(Player(1, "Тестовый игрок", source="fixture"), analysis, tmp_path)
    assert path.exists()
    assert path.stat().st_size > 20_000
    assert path.read_bytes().startswith(b"%PDF")
