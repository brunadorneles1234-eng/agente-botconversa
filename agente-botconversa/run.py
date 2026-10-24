"""
Agente Botconversa — Orquestrador Principal
Executado diariamente pelo Windows Task Scheduler.
"""
import json
import logging
import os
import sys
import webbrowser
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from src.config_loader import load_config, list_clients, ConfigError
from src.collector import collect_conversations, collect_webhook_metrics, CollectorError
from src.analyzer import analyze
from src.alert_detector import detect_alerts
from src.dashboard_generator import generate_dashboard

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "dados")
REPORTS_DIR = os.path.join(BASE_DIR, "relatorios")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "erros.log"),
    level=logging.ERROR,
    format="%(asctime)s — %(message)s",
)


def load_history(client_name: str, days: int = 90) -> list:
    history = []
    data_path = os.path.join(DATA_DIR, client_name)
    if not os.path.isdir(data_path):
        return history

    today = date.today()
    for i in range(1, days + 1):
        d = (today - timedelta(days=i)).isoformat()
        filepath = os.path.join(data_path, f"{d}.json")
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                entry = json.load(f)
                history.append({"date": d, **entry})

    return list(reversed(history))


def save_metrics(client_name: str, date_str: str, metrics: dict) -> None:
    path = os.path.join(DATA_DIR, client_name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, f"{date_str}.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)


def process_client(client_folder: str, yesterday: str) -> str | None:
    client_name = os.path.basename(client_folder)
    try:
        config = load_config(client_folder)
        nome = config.get("nome_cliente", client_name)
        print(f"  Coletando dados de: {nome}")

        conversations = collect_conversations(config["botconversa_api_key"], yesterday)
        metrics = analyze(conversations, config)
        alerts = detect_alerts(conversations, config)

        # Enriquece métricas com dados de tempo do servidor webhook
        webhook_url = config.get("webhook_server_url")
        webhook_secret = config.get("webhook_secret")
        webhook_cliente = config.get("webhook_cliente_id", client_name)
        if webhook_url and webhook_secret:
            try:
                wh = collect_webhook_metrics(webhook_url, webhook_secret, webhook_cliente, yesterday)
                metrics["avg_tempo_espera_segundos"] = wh.get("avg_tempo_espera_segundos")
                metrics["avg_tempo_atendimento_segundos"] = wh.get("avg_tempo_atendimento_segundos")
                metrics["webhook_por_unidade"] = wh.get("por_unidade", {})
                metrics["webhook_por_atendente"] = wh.get("por_atendente", {})
                metrics["total_confirmados"] = wh.get("total_confirmados", 0)
                metrics["total_encerrados"] = wh.get("total_encerrados", 0)
            except CollectorError as e:
                print(f"  Aviso: dados de tempo não disponíveis — {e}")

        history = load_history(client_name)

        save_metrics(client_name, yesterday, {
            "total_conversations": metrics["total_conversations"],
            "ai_resolved": metrics["ai_resolved"],
            "transferred_to_team": metrics["transferred_to_team"],
            "avg_tempo_espera_segundos": metrics.get("avg_tempo_espera_segundos"),
            "avg_tempo_atendimento_segundos": metrics.get("avg_tempo_atendimento_segundos"),
        })

        report_dir = os.path.join(REPORTS_DIR, client_name)
        dashboard_path = generate_dashboard(
            metrics=metrics,
            alerts=alerts,
            history=history,
            client_name=nome,
            date=yesterday,
            output_path=report_dir,
        )
        print(f"  Dashboard gerado: {dashboard_path}")
        return dashboard_path

    except ConfigError as e:
        msg = f"[{client_name}] Erro de configuração: {e}"
        print(f"  ERRO: {msg}")
        logging.error(msg)
    except CollectorError as e:
        msg = f"[{client_name}] Erro na API: {e}"
        print(f"  ERRO: {msg}")
        logging.error(msg)
    except Exception as e:
        msg = f"[{client_name}] Erro inesperado: {e}"
        print(f"  ERRO: {msg}")
        logging.error(msg, exc_info=True)

    return None


def main():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    print(f"Agente Botconversa — {yesterday}")
    print("=" * 50)

    os.makedirs(LOGS_DIR, exist_ok=True)

    clients = list_clients(CONFIG_DIR)
    if not clients:
        print("Nenhum cliente configurado em config/")
        sys.exit(0)

    dashboards = []
    for client in clients:
        client_folder = os.path.join(CONFIG_DIR, client)
        print(f"\nCliente: {client}")
        path = process_client(client_folder, yesterday)
        if path:
            dashboards.append(path)

    print("\n" + "=" * 50)
    print(f"Concluído: {len(dashboards)}/{len(clients)} clientes processados")

    for path in dashboards:
        webbrowser.open(f"file:///{path.replace(os.sep, '/')}")


if __name__ == "__main__":
    main()
