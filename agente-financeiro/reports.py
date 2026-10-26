from database import (
    get_transactions_by_date,
    get_transactions_by_month,
    get_category_total_month,
    list_dividas,
    get_limit,
)


def _fmt_money(value: float) -> str:
    """Format float as R$ 1.234,56"""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _progress_bar(pct: float, width: int = 8) -> str:
    filled = round(pct / 100 * width)
    filled = max(0, min(width, filled))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def format_daily_summary(db_path: str, date: str) -> str:
    transactions = get_transactions_by_date(db_path, date)
    despesas = [t for t in transactions if t["tipo"] == "despesa"]
    if not despesas:
        return "Nenhum gasto registrado hoje."

    by_person: dict[str, list] = {}
    for t in despesas:
        pessoa = t["pessoa"].capitalize()
        by_person.setdefault(pessoa, []).append(t)

    lines = [f"📊 Resumo do dia {date}"]
    total_dia = 0.0
    for pessoa, txns in sorted(by_person.items()):
        total_pessoa = sum(t["valor"] for t in txns)
        total_dia += total_pessoa
        lines.append(f"\n👤 {pessoa} — {_fmt_money(total_pessoa)}")
        for t in txns:
            lines.append(f"  • {t['descricao']} ({t['categoria']}): {_fmt_money(t['valor'])}")

    lines.append(f"\n💰 Total do dia: {_fmt_money(total_dia)}")
    return "\n".join(lines)


def format_monthly_summary(db_path: str, year: int, month: int) -> str:
    transactions = get_transactions_by_month(db_path, year, month)
    receitas = sum(t["valor"] for t in transactions if t["tipo"] == "receita")
    despesas_total = sum(t["valor"] for t in transactions if t["tipo"] == "despesa")
    saldo = receitas - despesas_total

    cat_totals: dict[str, float] = {}
    for t in transactions:
        if t["tipo"] == "despesa":
            cat_totals[t["categoria"]] = cat_totals.get(t["categoria"], 0.0) + t["valor"]
    top5 = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    lines = [f"📅 Resumo de {month:02d}/{year}"]
    lines.append(f"💚 Receitas: {_fmt_money(receitas)}")
    lines.append(f"🔴 Despesas: {_fmt_money(despesas_total)}")
    lines.append(f"💼 Saldo: {_fmt_money(saldo)}")

    if top5:
        lines.append("\n🏆 Top categorias:")
        for cat, val in top5:
            lines.append(f"  • {cat}: {_fmt_money(val)}")

    dividas = list_dividas(db_path)
    if dividas:
        lines.append("\n📋 Dívidas ativas:")
        for d in dividas:
            pct = (d["valor_pago"] / d["valor_total"] * 100) if d["valor_total"] else 0
            bar = _progress_bar(pct)
            lines.append(f"  • {d['nome']}: {bar} {pct:.0f}%")

    return "\n".join(lines)


def format_dividas(db_path: str) -> str:
    dividas = list_dividas(db_path)
    if not dividas:
        return "Nenhuma dívida ativa."

    lines = ["📋 Dívidas ativas:"]
    for d in dividas:
        pago = d["valor_pago"]
        total = d["valor_total"]
        restante = total - pago
        pct = (pago / total * 100) if total else 0
        bar = _progress_bar(pct)
        lines.append(
            f"\n💳 {d['nome']}\n"
            f"  Total: {_fmt_money(total)} | Pago: {_fmt_money(pago)} | Restante: {_fmt_money(restante)}\n"
            f"  Vencimento: dia {d['vencimento_dia']} | Parcela: {_fmt_money(d['valor_parcela'])}\n"
            f"  {bar} {pct:.0f}%"
        )
    return "\n".join(lines)


def check_category_alert(db_path: str, categoria: str, novo_valor: float, year: int, month: int) -> str | None:
    limite = get_limit(db_path, categoria)
    if limite is None:
        return None

    total_atual = get_category_total_month(db_path, categoria, year, month)
    total_com_novo = total_atual + novo_valor
    pct = total_com_novo / limite * 100

    if pct >= 100:
        return (
            f"⚠️ Limite de {categoria} atingido! "
            f"{_fmt_money(total_com_novo)} de {_fmt_money(limite)} ({pct:.0f}%)"
        )
    if pct >= 80:
        return (
            f"🔔 Atenção: {categoria} em {pct:.0f}% do limite. "
            f"{_fmt_money(total_com_novo)} de {_fmt_money(limite)}"
        )
    return None
