import pytest
from unittest.mock import patch, MagicMock
from claude_parser import parse_transaction, parse_extrato


def make_mock_response(content: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    return msg


@pytest.fixture
def mock_anthropic(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("claude_parser.anthropic.Anthropic", lambda api_key: MagicMock(messages=MagicMock(create=mock)))
    return mock


def test_parse_gasto_fast_food(mock_anthropic):
    mock_anthropic.return_value = make_mock_response(
        '{"valor": 45.0, "descricao": "iFood pizza", "categoria": "fast_food", "tipo": "despesa"}'
    )
    result = parse_transaction("ifood pizza R$45", "bruna", "fake-key")
    assert result["valor"] == 45.0
    assert result["categoria"] == "fast_food"
    assert result["tipo"] == "despesa"


def test_parse_receita(mock_anthropic):
    mock_anthropic.return_value = make_mock_response(
        '{"valor": 4500.0, "descricao": "salário", "categoria": "outros", "tipo": "receita"}'
    )
    result = parse_transaction("recebi salário R$4500", "bruna", "fake-key")
    assert result["tipo"] == "receita"


def test_parse_mensagem_ambigua_retorna_none(mock_anthropic):
    mock_anthropic.return_value = make_mock_response("null")
    result = parse_transaction("fui ao mercado", "bruna", "fake-key")
    assert result is None


def test_parse_extrato_retorna_lista(mock_anthropic):
    mock_anthropic.return_value = make_mock_response(
        '[{"valor": 120.0, "descricao": "Supermercado Extra", "categoria": "mercado", "tipo": "despesa"}]'
    )
    result = parse_extrato("26/10 Supermercado Extra -120,00", "fake-key")
    assert len(result) == 1
    assert result[0]["valor"] == 120.0


def test_parse_transaction_json_invalido_retorna_none(mock_anthropic):
    mock_anthropic.return_value = make_mock_response("isso não é json")
    result = parse_transaction("algum texto", "bruna", "fake-key")
    assert result is None


def test_parse_extrato_json_invalido_retorna_lista_vazia(mock_anthropic):
    mock_anthropic.return_value = make_mock_response("não é json")
    result = parse_extrato("extrato qualquer", "fake-key")
    assert result == []
