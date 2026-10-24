"""
Servidor Webhook — Agente Botconversa
Recebe eventos dos fluxos do Botconversa e salva métricas anonimizadas.
"""
import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DB_PATH = os.environ.get("DB_PATH", "eventos.db")
SECRET_KEY = os.environ.get("WEBHOOK_SECRET", "trocar-por-chave-secreta")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anon_id TEXT NOT NULL,
                cliente TEXT NOT NULL,
                unidade TEXT NOT NULL,
                evento TEXT NOT NULL,
                atendente TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_eventos_cliente_data
                ON eventos (cliente, timestamp);
            CREATE INDEX IF NOT EXISTS idx_eventos_anon_id
                ON eventos (anon_id);
        """)


def anonimizar_id(subscriber_id: str, cliente: str) -> str:
    raw = f"lgpd:{cliente}:{subscriber_id}"
    return "sub_" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def validar_token(req) -> bool:
    token = req.headers.get("X-Webhook-Secret", "")
    return token == SECRET_KEY


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route("/webhook/<cliente>/<unidade>/<evento>", methods=["POST"])
def receber_evento(cliente, unidade, evento):
    """
    Recebe eventos do Botconversa.
    URL exemplo: https://seu-servidor.railway.app/webhook/neuropsico/parque/confirmado

    Eventos esperados:
    - confirmado: cliente confirmou presença
    - nao_confirmado: cliente não confirmou
    - bot_parou: bot transferiu para equipe
    - equipe_assumiu: atendente foi atribuído
    - encerrado: conversa encerrada
    """
    if not validar_token(request):
        return jsonify({"erro": "Token inválido"}), 401

    dados = request.get_json(silent=True) or {}

    subscriber_id = str(dados.get("subscriber_id", dados.get("id", "desconhecido")))
    atendente_raw = dados.get("atendente", dados.get("manager", dados.get("assigned_to", "")))
    timestamp = dados.get("timestamp") or datetime.now(timezone.utc).isoformat()

    anon_id = anonimizar_id(subscriber_id, cliente)

    eventos_validos = {"confirmado", "nao_confirmado", "bot_parou", "equipe_assumiu", "encerrado"}
    if evento not in eventos_validos:
        return jsonify({"erro": f"Evento inválido. Use: {eventos_validos}"}), 400

    with get_db() as conn:
        conn.execute(
            """INSERT INTO eventos (anon_id, cliente, unidade, evento, atendente, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (anon_id, cliente.lower(), unidade.lower(), evento, atendente_raw or None, timestamp)
        )

    app.logger.info(f"Evento registrado: {cliente}/{unidade}/{evento} ({anon_id})")
    return jsonify({"status": "ok", "anon_id": anon_id}), 201


@app.route("/metricas/<cliente>/<data>", methods=["GET"])
def metricas_dia(cliente, data):
    """
    Retorna métricas do dia para o agente Python consumir.
    data formato: YYYY-MM-DD
    """
    if not validar_token(request):
        return jsonify({"erro": "Token inválido"}), 401

    with get_db() as conn:
        rows = conn.execute(
            """SELECT anon_id, unidade, evento, atendente, timestamp
               FROM eventos
               WHERE cliente = ? AND DATE(timestamp) = ?
               ORDER BY timestamp""",
            (cliente.lower(), data)
        ).fetchall()

    eventos = [dict(r) for r in rows]

    metricas = calcular_metricas(eventos)

    return jsonify({"data": data, "cliente": cliente, "metricas": metricas, "eventos": eventos})


def calcular_metricas(eventos: list) -> dict:
    confirmados = [e for e in eventos if e["evento"] == "confirmado"]
    nao_confirmados = [e for e in eventos if e["evento"] == "nao_confirmado"]
    transferencias = [e for e in eventos if e["evento"] == "bot_parou"]
    atendimentos = [e for e in eventos if e["evento"] == "equipe_assumiu"]
    encerrados = [e for e in eventos if e["evento"] == "encerrado"]

    por_unidade = {}
    for e in eventos:
        u = e["unidade"]
        if u not in por_unidade:
            por_unidade[u] = {"confirmados": 0, "transferencias": 0, "atendimentos": 0}
        if e["evento"] == "confirmado":
            por_unidade[u]["confirmados"] += 1
        elif e["evento"] == "bot_parou":
            por_unidade[u]["transferencias"] += 1
        elif e["evento"] == "equipe_assumiu":
            por_unidade[u]["atendimentos"] += 1

    tempos_espera = calcular_tempos_par(transferencias, atendimentos)
    tempos_atendimento = calcular_tempos_par(atendimentos, encerrados)

    por_atendente = {}
    for e in atendimentos:
        att = e.get("atendente") or "desconhecido"
        if att not in por_atendente:
            por_atendente[att] = {"atendimentos": 0, "avg_tempo_atendimento_segundos": None}
        por_atendente[att]["atendimentos"] += 1

    # tempo médio de atendimento por atendente
    for att in por_atendente:
        ass = [e for e in atendimentos if (e.get("atendente") or "desconhecido") == att]
        enc = [e for e in encerrados if (e.get("atendente") or "desconhecido") == att]
        por_atendente[att]["avg_tempo_atendimento_segundos"] = calcular_tempos_par(ass, enc)

    return {
        "total_confirmados": len(confirmados),
        "total_nao_confirmados": len(nao_confirmados),
        "total_transferencias": len(transferencias),
        "total_atendimentos": len(atendimentos),
        "total_encerrados": len(encerrados),
        "avg_tempo_espera_segundos": tempos_espera,
        "avg_tempo_atendimento_segundos": tempos_atendimento,
        "por_unidade": por_unidade,
        "por_atendente": por_atendente,
    }


def calcular_tempos_par(eventos_inicio: list, eventos_fim: list) -> float | None:
    """Calcula tempo médio entre dois tipos de evento pelo mesmo anon_id."""
    inicio_por_id = {e["anon_id"]: e["timestamp"] for e in eventos_inicio}
    tempos = []
    for e in eventos_fim:
        anon_id = e["anon_id"]
        if anon_id in inicio_por_id:
            try:
                t_inicio = datetime.fromisoformat(inicio_por_id[anon_id].replace("Z", "+00:00"))
                t_fim = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
                diff = (t_fim - t_inicio).total_seconds()
                if 0 < diff < 86400:
                    tempos.append(diff)
            except Exception:
                pass
    return round(sum(tempos) / len(tempos), 1) if tempos else None


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
