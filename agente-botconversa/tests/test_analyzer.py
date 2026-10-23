import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.analyzer import analyze

SAMPLE_CONFIG = {
    "unidades": {"f1": "Centro", "f2": "Norte"},
    "atendentes": {"u1": "Centro", "u2": "Norte"},
    "tempo_alerta_ia_minutos": 5,
    "tempo_alerta_equipe_minutos": 10,
}


def make_conv(**kwargs):
    base = {
        "anon_id": "conv_test",
        "flow_id": "f1",
        "status": "resolved",
        "ai_response_seconds": 60,
        "team_takeover_seconds": None,
        "attendant_id": "u1",
        "messages": [],
    }
    base.update(kwargs)
    return base


def test_analyze_total_conversations():
    convs = [make_conv(), make_conv(), make_conv()]
    result = analyze(convs, SAMPLE_CONFIG)
    assert result["total_conversations"] == 3


def test_analyze_ai_response_time():
    convs = [make_conv(ai_response_seconds=120), make_conv(ai_response_seconds=60)]
    result = analyze(convs, SAMPLE_CONFIG)
    assert result["avg_ai_response_seconds"] == 90.0


def test_analyze_team_takeover_ignores_none():
    convs = [make_conv(team_takeover_seconds=300), make_conv(team_takeover_seconds=None)]
    result = analyze(convs, SAMPLE_CONFIG)
    assert result["avg_team_takeover_seconds"] == 300.0


def test_analyze_team_takeover_all_none():
    convs = [make_conv(team_takeover_seconds=None)]
    result = analyze(convs, SAMPLE_CONFIG)
    assert result["avg_team_takeover_seconds"] is None


def test_analyze_by_unit():
    convs = [
        make_conv(flow_id="f1"),
        make_conv(flow_id="f1"),
        make_conv(flow_id="f2"),
    ]
    result = analyze(convs, SAMPLE_CONFIG)
    assert result["by_unit"]["Centro"]["total"] == 2
    assert result["by_unit"]["Norte"]["total"] == 1


def test_analyze_by_attendant():
    convs = [make_conv(attendant_id="u1"), make_conv(attendant_id="u1")]
    result = analyze(convs, SAMPLE_CONFIG)
    assert result["by_attendant"]["u1"]["total"] == 2


def test_analyze_transferred_vs_resolved():
    convs = [
        make_conv(status="resolved", team_takeover_seconds=None),
        make_conv(status="transferred", team_takeover_seconds=300),
    ]
    result = analyze(convs, SAMPLE_CONFIG)
    assert result["ai_resolved"] == 1
    assert result["transferred_to_team"] == 1
