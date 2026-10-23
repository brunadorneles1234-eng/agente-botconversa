import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.dashboard_generator import generate_dashboard

SAMPLE_METRICS = {
    "total_conversations": 47,
    "ai_resolved": 40,
    "transferred_to_team": 7,
    "avg_ai_response_seconds": 90.0,
    "avg_team_takeover_seconds": 300.0,
    "by_unit": {"Centro": {"total": 30, "avg_ai_response_seconds": 85.0}},
    "by_attendant": {"u1": {"total": 15, "avg_response_seconds": 90.0}},
}


def test_dashboard_created(tmp_path):
    path = generate_dashboard(
        metrics=SAMPLE_METRICS, alerts=[], history=[],
        client_name="Teste", date="2026-10-22",
        output_path=str(tmp_path)
    )
    assert Path(path).exists()
    assert path.endswith(".html")


def test_dashboard_shows_total_conversations(tmp_path):
    path = generate_dashboard(
        metrics={**SAMPLE_METRICS, "total_conversations": 47},
        alerts=[], history=[],
        client_name="Teste", date="2026-10-22",
        output_path=str(tmp_path)
    )
    content = Path(path).read_text(encoding="utf-8")
    assert "47" in content


def test_dashboard_shows_alert(tmp_path):
    alerts = [{"tipo": "ia_lenta", "anon_id": "conv_abc", "descricao": "IA lenta", "botconversa_url": None}]
    path = generate_dashboard(
        metrics=SAMPLE_METRICS, alerts=alerts, history=[],
        client_name="Teste", date="2026-10-22",
        output_path=str(tmp_path)
    )
    content = Path(path).read_text(encoding="utf-8")
    assert "conv_abc" in content


def test_dashboard_no_history_shows_message(tmp_path):
    path = generate_dashboard(
        metrics=SAMPLE_METRICS, alerts=[], history=[],
        client_name="Teste", date="2026-10-22",
        output_path=str(tmp_path)
    )
    content = Path(path).read_text(encoding="utf-8")
    assert "dados insuficientes" in content.lower()


def test_dashboard_filename_includes_date(tmp_path):
    path = generate_dashboard(
        metrics=SAMPLE_METRICS, alerts=[], history=[],
        client_name="Teste", date="2026-10-22",
        output_path=str(tmp_path)
    )
    assert "2026-10-22" in path
