import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.anonymizer import anonymize_conversation


def test_anonymize_removes_phone():
    raw = {"id": "conv_123", "contact_phone": "51999999999", "messages": []}
    result = anonymize_conversation(raw)
    assert "contact_phone" not in result
    assert "contact_name" not in result


def test_anonymize_preserves_anon_id():
    raw = {"id": "conv_123", "contact_phone": "51999999999"}
    result = anonymize_conversation(raw)
    assert result["anon_id"].startswith("conv_")
    assert result["anon_id"] != "conv_123"


def test_anonymize_same_input_same_output():
    raw = {"id": "conv_123", "contact_phone": "51999999999"}
    assert anonymize_conversation(raw)["anon_id"] == anonymize_conversation(raw)["anon_id"]


def test_anonymize_removes_message_content():
    raw = {
        "id": "c1",
        "messages": [{"text": "meu cpf é 123", "sender": "contact"}]
    }
    result = anonymize_conversation(raw)
    assert "text" not in result["messages"][0]
    assert result["messages"][0]["sender"] == "contact"


def test_anonymize_removes_all_personal_fields():
    raw = {
        "id": "c2",
        "contact_phone": "51999",
        "contact_name": "João",
        "contact_email": "joao@test.com",
        "contact_cpf": "123.456.789-00",
        "flow_id": "f1",
        "status": "resolved"
    }
    result = anonymize_conversation(raw)
    assert "contact_phone" not in result
    assert "contact_name" not in result
    assert "contact_email" not in result
    assert "contact_cpf" not in result
    assert result["flow_id"] == "f1"
    assert result["status"] == "resolved"
