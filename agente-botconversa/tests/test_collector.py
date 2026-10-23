import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.collector import collect_conversations, CollectorError

BASE_URL = "https://backend.botconversa.com.br/api/v1"


def test_collect_returns_anonymized(requests_mock):
    requests_mock.get(
        f"{BASE_URL}/webhook/conversation/",
        json={
            "results": [
                {"id": "c1", "contact_phone": "51999999999", "flow_id": "f1",
                 "status": "resolved", "messages": []}
            ],
            "next": None
        }
    )
    result = collect_conversations("test_key", "2026-10-22")
    assert len(result) == 1
    assert "contact_phone" not in result[0]
    assert "anon_id" in result[0]


def test_collect_api_error_raises(requests_mock):
    requests_mock.get(
        f"{BASE_URL}/webhook/conversation/",
        status_code=401
    )
    with pytest.raises(CollectorError, match="401"):
        collect_conversations("bad_key", "2026-10-22")


def test_collect_empty_day(requests_mock):
    requests_mock.get(
        f"{BASE_URL}/webhook/conversation/",
        json={"results": [], "next": None}
    )
    result = collect_conversations("test_key", "2026-10-22")
    assert result == []


def test_collect_paginates(requests_mock):
    requests_mock.get(
        f"{BASE_URL}/webhook/conversation/",
        [
            {"json": {"results": [{"id": "c1", "flow_id": "f1", "messages": []}],
                      "next": f"{BASE_URL}/webhook/conversation/?page=2"}},
            {"json": {"results": [{"id": "c2", "flow_id": "f1", "messages": []}],
                      "next": None}},
        ]
    )
    result = collect_conversations("test_key", "2026-10-22")
    assert len(result) == 2
