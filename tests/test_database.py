from database import (
    init_db, add_transaction, get_transactions_by_date,
    get_transactions_by_month, get_category_total_month,
    add_divida, list_dividas, update_divida_paid,
    get_limit, set_limit, get_all_limits,
)


def test_add_and_get_transaction(tmp_db):
    init_db(tmp_db)
    tid = add_transaction(tmp_db, "bruna", 45.0, "iFood pizza", "fast_food", "despesa", "2026-10-26")
    rows = get_transactions_by_date(tmp_db, "2026-10-26")
    assert len(rows) == 1
    assert rows[0]["valor"] == 45.0
    assert rows[0]["pessoa"] == "bruna"
    assert rows[0]["categoria"] == "fast_food"


def test_category_total_month(tmp_db):
    init_db(tmp_db)
    add_transaction(tmp_db, "bruna", 45.0, "iFood", "fast_food", "despesa", "2026-10-26")
    add_transaction(tmp_db, "renan", 30.0, "Burguer King", "fast_food", "despesa", "2026-10-20")
    total = get_category_total_month(tmp_db, "fast_food", 2026, 10)
    assert total == 75.0


def test_update_divida_paid_quita_quando_completo(tmp_db):
    init_db(tmp_db)
    did = add_divida(tmp_db, "Consignado", 1000.0, 100.0, 10, 5)
    result = update_divida_paid(tmp_db, did, 1000.0)
    assert result["status"] == "quitado"
    assert result["valor_pago"] == 1000.0


def test_update_divida_paid_nao_excede_total(tmp_db):
    init_db(tmp_db)
    did = add_divida(tmp_db, "Emprestimo", 500.0, 50.0, 10, 10)
    result = update_divida_paid(tmp_db, did, 600.0)
    assert result["valor_pago"] == 500.0
    assert result["status"] == "quitado"


def test_limit_crud(tmp_db):
    init_db(tmp_db)
    assert get_limit(tmp_db, "fast_food") is None
    set_limit(tmp_db, "fast_food", 200.0)
    assert get_limit(tmp_db, "fast_food") == 200.0
