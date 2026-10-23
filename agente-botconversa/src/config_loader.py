import json
import os


class ConfigError(Exception):
    pass


def load_config(client_folder: str) -> dict:
    path = os.path.join(client_folder, "config.json")
    if not os.path.exists(path):
        raise ConfigError(f"Arquivo config.json não encontrado em: {client_folder}")

    with open(path, encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"config.json inválido: {e}")

    if not config.get("botconversa_api_key"):
        raise ConfigError("botconversa_api_key ausente ou vazia no config.json")

    config.setdefault("tempo_alerta_ia_minutos", 5)
    config.setdefault("tempo_alerta_equipe_minutos", 10)
    config.setdefault("unidades", {})
    config.setdefault("atendentes", {})

    return config


def list_clients(base_path: str) -> list:
    if not os.path.isdir(base_path):
        return []
    return [
        name for name in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, name))
    ]
