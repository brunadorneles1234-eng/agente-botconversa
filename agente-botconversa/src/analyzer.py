def analyze(conversations: list, config: dict) -> dict:
    unidades = config.get("unidades", {})
    atendentes = config.get("atendentes", {})

    total = len(conversations)
    ai_resolved = 0
    transferred = 0
    ai_times = []
    takeover_times = []

    by_unit = {}
    by_attendant = {}

    for conv in conversations:
        status = conv.get("status", "")
        if conv.get("team_takeover_seconds") is not None:
            transferred += 1
            takeover_times.append(conv["team_takeover_seconds"])
        else:
            ai_resolved += 1

        ai_sec = conv.get("ai_response_seconds")
        if ai_sec is not None:
            ai_times.append(ai_sec)

        flow_id = conv.get("flow_id", "")
        unit_name = unidades.get(flow_id, flow_id)
        if unit_name not in by_unit:
            by_unit[unit_name] = {"total": 0, "ai_response_seconds": []}
        by_unit[unit_name]["total"] += 1
        if ai_sec is not None:
            by_unit[unit_name]["ai_response_seconds"].append(ai_sec)

        att_id = conv.get("attendant_id", "")
        if att_id:
            if att_id not in by_attendant:
                by_attendant[att_id] = {"total": 0, "response_seconds": []}
            by_attendant[att_id]["total"] += 1
            if ai_sec is not None:
                by_attendant[att_id]["response_seconds"].append(ai_sec)

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    by_unit_final = {
        name: {
            "total": data["total"],
            "avg_ai_response_seconds": avg(data["ai_response_seconds"]),
        }
        for name, data in by_unit.items()
    }

    by_att_final = {
        att_id: {
            "total": data["total"],
            "avg_response_seconds": avg(data["response_seconds"]),
        }
        for att_id, data in by_attendant.items()
    }

    return {
        "total_conversations": total,
        "ai_resolved": ai_resolved,
        "transferred_to_team": transferred,
        "avg_ai_response_seconds": avg(ai_times),
        "avg_team_takeover_seconds": avg(takeover_times),
        "by_unit": by_unit_final,
        "by_attendant": by_att_final,
    }
