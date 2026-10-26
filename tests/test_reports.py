from database import init_db, add_transaction, add_divida, set_limit
from reports import (
    format_daily_summary,
    format_monthly_summary,
    format_dividas,
    check_category_alert,
)


def test_daily_summary_com_gastos(tmp_db):
    init_db(tmp_db)
    add_transaction(tmp_db, "bruna", 60.0, "mercado", "mercado", "despesa", "2026-10-26")
    add_transaction(tmp_db, "renan", 40.0, "uber", "transporte", "despesa", "2026-10-26")
    summary = format_daily_summary(tmp_db, "2026-10-26")
    assert "R$ 60,00" in summary
    assert "Bruna" in summary
    assert "Renan" in summary
    assert "R$ 100,00" in summary  # total do dia


def test_daily_summary_sem_gastos(tmp_db):
    init_db(tmp_db)
    summary = format_daily_summary(tmp_db, "2026-10-26")
    assert "nenhum gasto" in summary.lower()


def test_category_alert_acima_limite(tmp_db):
    init_db(tmp_db)
    set_limit(tmp_db, "fast_food", 200.0)
    add_transaction(tmp_db, "bruna", 180.0, "iFood", "fast_food", "despesa", "2026-10-26")
    alert = check_category_alert(tmp_db, "fast_food", 30.0, 2026, 10)
    assert alert is not None
    assert "fast food" in alert.lower() or "fast_food" in alert.lower()


def test_category_alert_sem_limite_retorna_none(tmp_db):
    init_db(tmp_db)
    alert = check_category_alert(tmp_db, "fast_food", 50.0, 2026, 10)
    assert alert is None


def test_category_alert_limite_zero_retorna_none(tmp_db):
    init_db(tmp_db)
    set_limit(tmp_db, "fast_food", 0.0)
    alert = check_category_alert(tmp_db, "fast_food", 50.0, 2026, 10)
    assert alert is None


def test_format_dividas_lista(tmp_db):
    init_db(tmp_db)
    add_divida(tmp_db, "Consignado Caixa", 12000.0, 400.0, 30, 5)
    result = format_dividas(tmp_db)
    assert "Consignado Caixa" in result
    assert "R$ 12.000,00" in result or "12000" in result
