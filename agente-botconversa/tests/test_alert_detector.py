import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.alert_detector import detect_alerts

SAMPLE_CONFIG = {
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
        "repeated_messages": 0,
        "transfer_count": 0,
        "messages": [],
    }
    base.update(kwargs)
    return base


def test_alert_ai_slow_response():
    convs = [make_conv(anon_id="conv_abc", ai_response_seconds=400)]
    alerts = detect_alerts(convs, SAMPLE_CONFIG)
    assert any(a["tipo"] == "ia_lenta" and a["anon_id"] == "conv_abc" for a in alerts)


def test_alert_team_slow_takeover():
    convs = [make_conv(anon_id="conv_xyz", team_takeover_seconds=700)]
    alerts = detect_alerts(convs, SAMPLE_CONFIG)
    assert any(a["tipo"] == "equipe_lenta" for a in alerts)


def test_alert_abandoned():
    convs = [make_conv(anon_id="conv_abn", status="abandoned")]
    alerts = detect_alerts(convs, SAMPLE_CONFIG)
    assert any(a["tipo"] == "abandono" for a in alerts)


def test_alert_ai_loop():
    convs = [make_conv(anon_id="conv_loop", repeated_messages=3)]
    alerts = detect_alerts(convs, SAMPLE_CONFIG)
    assert any(a["tipo"] == "loop_ia" for a in alerts)


def test_alert_multiple_transfer():
    convs = [make_conv(anon_id="conv_mt", transfer_count=2)]
    alerts = detect_alerts(convs, SAMPLE_CONFIG)
    assert any(a["tipo"] == "transferencia_multipla" for a in alerts)


def test_no_alert_for_normal_conversation():
    convs = [make_conv(ai_response_seconds=60, status="resolved")]
    alerts = detect_alerts(convs, SAMPLE_CONFIG)
    assert alerts == []


def test_alert_has_required_fields():
    convs = [make_conv(anon_id="conv_slow", ai_response_seconds=400)]
    alerts = detect_alerts(convs, SAMPLE_CONFIG)
    alert = alerts[0]
    assert "tipo" in alert
    assert "anon_id" in alert
    assert "descricao" in alert
    assert "botconversa_url" in alert
