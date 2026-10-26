import json
import anthropic

try:
    from config import VALID_CATEGORIES
except Exception:
    VALID_CATEGORIES = [
        "fast_food", "restaurante", "mercado", "transporte", "combustivel",
        "saude", "educacao", "lazer", "moradia", "contas", "roupas",
        "assinaturas", "outros",
    ]

TRANSACTION_SYSTEM_PROMPT = """Você é um parser de transações financeiras pessoais em português.
Dado um texto, extraia a transação financeira e retorne um JSON puro com os campos:
- valor: número float positivo
- descricao: string curta descrevendo a transação
- categoria: uma das categorias válidas
- tipo: "despesa" ou "receita"

Categorias válidas: {categories}

Se o texto não descrever uma transação financeira clara com valor monetário, retorne apenas: null

Retorne SOMENTE o JSON ou null, sem explicações."""

EXTRATO_SYSTEM_PROMPT = """Você é um parser de extratos bancários em português.
Dado um extrato bancário, extraia todas as transações e retorne um JSON array.
Cada item do array deve ter:
- valor: número float positivo
- descricao: string curta descrevendo a transação
- categoria: uma das categorias válidas
- tipo: "despesa" ou "receita"

Categorias válidas: {categories}

Se não houver transações identificáveis, retorne: []

Retorne SOMENTE o JSON array, sem explicações."""


def _validate_transaction(item: object) -> bool:
    """Return True if item is a valid transaction dict."""
    if not isinstance(item, dict):
        return False
    if not isinstance(item.get("valor"), (int, float)):
        return False
    if not isinstance(item.get("descricao"), str):
        return False
    if item.get("categoria") not in VALID_CATEGORIES:
        return False
    if item.get("tipo") not in ("despesa", "receita"):
        return False
    return True


def parse_transaction(text: str, pessoa: str, api_key: str) -> dict | None:
    client = anthropic.Anthropic(api_key=api_key)
    system = TRANSACTION_SYSTEM_PROMPT.format(categories=", ".join(VALID_CATEGORIES))
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system=system,
            messages=[{"role": "user", "content": f"Pessoa: {pessoa}\nMensagem: {text}"}],
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)
    except (json.JSONDecodeError, IndexError, Exception):
        return None
    if result is None:
        return None
    if not _validate_transaction(result):
        return None
    return result


def parse_extrato(text: str, api_key: str) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)
    system = EXTRATO_SYSTEM_PROMPT.format(categories=", ".join(VALID_CATEGORIES))
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)
    except (json.JSONDecodeError, IndexError, Exception):
        return []
    if not isinstance(result, list):
        return []
    return [item for item in result if _validate_transaction(item)]
