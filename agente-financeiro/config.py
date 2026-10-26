import os
from categories import VALID_CATEGORIES

def _require(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"Variável de ambiente obrigatória ausente: {name}")
    return value


TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_GROUP_ID: int = int(_require("TELEGRAM_GROUP_ID"))
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")

_bruna_id: int = int(_require("TELEGRAM_USER_BRUNA_ID"))
_renan_id: int = int(_require("TELEGRAM_USER_RENAN_ID"))

DB_PATH: str = os.environ.get("DB_PATH", "financeiro.db")

USER_MAP: dict[int, str] = {
    _bruna_id: "bruna",
    _renan_id: "renan",
}
