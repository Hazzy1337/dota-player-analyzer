from dota_analyzer.analytics.engine import analyze_matches
from dota_analyzer.analytics.sessions import split_sessions
from dota_analyzer.recommendations.engine import build_recommendations


def test_overview_kda_wr_and_aggregations(sample_matches):
    result = analyze_matches(sample_matches)
    assert result["overview"]["matches"] == 30
    assert result["overview"]["wins"] == 20
    assert result["overview"]["losses"] == 10
    assert result["overview"]["winrate"] == 66.67
    assert result["overview"]["kda"] is not None
    assert result["heroes"][0]["name"] == "Anti-Mage"
    assert result["heroes"][0]["matches"] == 18
    assert result["roles"]["main_role"] == "Pos 1"
    assert result["streaks"]["longest_loss"] == 1
    assert result["deaths"]["buckets"][-1]["name"] == "10+"


def test_session_split(sample_matches):
    sessions = split_sessions(sample_matches)
    assert len(sessions) == 30
    sample_matches[1].start_time = sample_matches[0].start_time + sample_matches[0].duration + 60 * 30
    assert len(split_sessions(sample_matches)) == 29


def test_coaching_output_is_actionable(sample_matches):
    analysis = analyze_matches(sample_matches)
    result = build_recommendations(analysis, language="ru")
    assert result["overall_rating"]["score"] is not None
    assert result["coach_summary"]
    assert len(result["rating_breakdown"]) >= 4
    assert len(result["top_leaks"]) >= 3
    assert len(result["quick_actions"]) == 3
    assert result["next_30_games_plan"]["main_focus"]
