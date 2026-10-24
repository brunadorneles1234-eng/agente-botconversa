import requests
from src.anonymizer import anonymize_conversation

BASE_URL = "https://backend.botconversa.com.br/api/v1"


class CollectorError(Exception):
    pass


def collect_conversations(api_key: str, date: str) -> list:
    headers = {"api-key": api_key}
    params = {"date": date}
    url = f"{BASE_URL}/webhook/conversation/"
    conversations = []

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            raise CollectorError(f"Erro na API Botconversa: {response.status_code} — {response.text[:200]}")

        data = response.json()
        for conv in data.get("results", []):
            conversations.append(anonymize_conversation(conv))

        url = data.get("next")
        params = {}

    return conversations


def collect_webhook_metrics(webhook_url: str, webhook_secret: str, cliente: str, date: str) -> dict:
    """Busca métricas agregadas do servidor webhook (tempos de espera e atendimento)."""
    headers = {"X-Webhook-Secret": webhook_secret}
    url = f"{webhook_url}/metricas/{cliente}/{date}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            raise CollectorError(f"Erro no servidor webhook: {response.status_code}")
        return response.json().get("metricas", {})
    except requests.RequestException as e:
        raise CollectorError(f"Erro de conexão com webhook server: {e}")
