def detect_alerts(conversations: list, config: dict) -> list:
    alerta_ia_seg = config.get("tempo_alerta_ia_minutos", 5) * 60
    alerta_equipe_seg = config.get("tempo_alerta_equipe_minutos", 10) * 60
    alerts = []

    for conv in conversations:
        anon_id = conv.get("anon_id", "")
        url = conv.get("botconversa_url", None)

        ai_sec = conv.get("ai_response_seconds")
        if ai_sec is not None and ai_sec > alerta_ia_seg:
            alerts.append({
                "tipo": "ia_lenta",
                "anon_id": anon_id,
                "descricao": f"IA sem resposta por {ai_sec // 60}min {ai_sec % 60}s (limite: {config['tempo_alerta_ia_minutos']}min)",
                "botconversa_url": url,
            })

        takeover_sec = conv.get("team_takeover_seconds")
        if takeover_sec is not None and takeover_sec > alerta_equipe_seg:
            alerts.append({
                "tipo": "equipe_lenta",
                "anon_id": anon_id,
                "descricao": f"Equipe demorou {takeover_sec // 60}min para assumir (limite: {config['tempo_alerta_equipe_minutos']}min)",
                "botconversa_url": url,
            })

        if conv.get("status") == "abandoned":
            alerts.append({
                "tipo": "abandono",
                "anon_id": anon_id,
                "descricao": "Cliente saiu sem resolução",
                "botconversa_url": url,
            })

        if conv.get("repeated_messages", 0) >= 3:
            alerts.append({
                "tipo": "loop_ia",
                "anon_id": anon_id,
                "descricao": f"IA repetiu a mesma mensagem {conv['repeated_messages']}x",
                "botconversa_url": url,
            })

        if conv.get("transfer_count", 0) > 1:
            alerts.append({
                "tipo": "transferencia_multipla",
                "anon_id": anon_id,
                "descricao": f"Conversa transferida {conv['transfer_count']}x para equipe",
                "botconversa_url": url,
            })

    return alerts
