import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config_loader import load_config, list_clients, ConfigError

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_load_config_valid():
    config = load_config(os.path.join(FIXTURES, "valid_client"))
    assert config["nome_cliente"] == "Cliente Teste"
    assert config["botconversa_api_key"] == "key_test_123"
    assert config["tempo_alerta_ia_minutos"] == 5


def test_load_config_missing_file():
    with pytest.raises(ConfigError):
        load_config(os.path.join(FIXTURES, "nonexistent_client"))


def test_load_config_missing_api_key():
    with pytest.raises(ConfigError, match="botconversa_api_key"):
        load_config(os.path.join(FIXTURES, "invalid_client"))


def test_load_config_defaults():
    config = load_config(os.path.join(FIXTURES, "valid_client"))
    assert config["tempo_alerta_ia_minutos"] == 5
    assert config["tempo_alerta_equipe_minutos"] == 10


def test_list_clients():
    clients = list_clients(os.path.join(FIXTURES, "multi_client"))
    assert "cliente_a" in clients
    assert "cliente_b" in clients
