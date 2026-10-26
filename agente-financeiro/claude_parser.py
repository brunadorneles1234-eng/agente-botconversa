import json
import anthropic

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


def parse_transaction(text: str, pessoa: str, api_key: str) -> dict | None:
    client = anthropic.Anthropic(api_key=api_key)
    system = TRANSACTION_SYSTEM_PROMPT.format(categories=", ".join(VALID_CATEGORIES))
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": f"Pessoa: {pessoa}\nMensagem: {text}"}],
    )
    raw = response.content[0].text.strip()
    try:
        result = json.loads(raw)
        return result  # None if "null", dict otherwise
    except (json.JSONDecodeError, IndexError):
        return None


def parse_extrato(text: str, api_key: str) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)
    system = EXTRATO_SYSTEM_PROMPT.format(categories=", ".join(VALID_CATEGORIES))
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": text}],
    )
    raw = response.content[0].text.strip()
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        return []
    except (json.JSONDecodeError, IndexError):
        return []
