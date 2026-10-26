import sqlite3


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pessoa TEXT NOT NULL,
                valor REAL NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                tipo TEXT NOT NULL,
                data TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dividas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                valor_total REAL NOT NULL,
                valor_pago REAL NOT NULL DEFAULT 0.0,
                valor_parcela REAL NOT NULL,
                parcelas_restantes INTEGER NOT NULL,
                vencimento_dia INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'ativo'
            );

            CREATE TABLE IF NOT EXISTS limites_categoria (
                categoria TEXT PRIMARY KEY,
                limite_mensal REAL NOT NULL
            );
        """)
    conn.close()


def add_transaction(db_path: str, pessoa: str, valor: float, descricao: str,
                    categoria: str, tipo: str, data: str) -> int:
    conn = sqlite3.connect(db_path)
    with conn:
        cur = conn.execute(
            "INSERT INTO transacoes (pessoa, valor, descricao, categoria, tipo, data) VALUES (?, ?, ?, ?, ?, ?)",
            (pessoa, valor, descricao, categoria, tipo, data)
        )
    rowid = cur.lastrowid
    conn.close()
    return rowid


def get_transactions_by_date(db_path: str, date: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM transacoes WHERE DATE(data) = ?", (date,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_transactions_by_month(db_path: str, year: int, month: int) -> list[dict]:
    ym = f"{year:04d}-{month:02d}"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM transacoes WHERE strftime('%Y-%m', data) = ?", (ym,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_category_total_month(db_path: str, categoria: str, year: int, month: int) -> float:
    ym = f"{year:04d}-{month:02d}"
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT SUM(valor) FROM transacoes WHERE tipo = 'despesa' AND categoria = ? AND strftime('%Y-%m', data) = ?",
        (categoria, ym)
    )
    result = cur.fetchone()[0]
    conn.close()
    return result or 0.0


def add_divida(db_path: str, nome: str, valor_total: float, valor_parcela: float,
               parcelas_restantes: int, vencimento_dia: int) -> int:
    conn = sqlite3.connect(db_path)
    with conn:
        cur = conn.execute(
            "INSERT INTO dividas (nome, valor_total, valor_parcela, parcelas_restantes, vencimento_dia) VALUES (?, ?, ?, ?, ?)",
            (nome, valor_total, valor_parcela, parcelas_restantes, vencimento_dia)
        )
    rowid = cur.lastrowid
    conn.close()
    return rowid


def list_dividas(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM dividas WHERE status != 'quitado' ORDER BY vencimento_dia")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def update_divida_paid(db_path: str, divida_id: int, valor_adicional: float) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM dividas WHERE id = ?", (divida_id,))
    row = dict(cur.fetchone())
    novo_pago = min(row["valor_pago"] + valor_adicional, row["valor_total"])
    novo_status = "quitado" if novo_pago >= row["valor_total"] else row["status"]
    with conn:
        conn.execute(
            "UPDATE dividas SET valor_pago = ?, status = ? WHERE id = ?",
            (novo_pago, novo_status, divida_id)
        )
    cur = conn.execute("SELECT * FROM dividas WHERE id = ?", (divida_id,))
    updated = dict(cur.fetchone())
    conn.close()
    return updated


def get_limit(db_path: str, categoria: str) -> float | None:
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT limite_mensal FROM limites_categoria WHERE categoria = ?", (categoria,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_limit(db_path: str, categoria: str, limite_mensal: float) -> None:
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute(
            "INSERT INTO limites_categoria (categoria, limite_mensal) VALUES (?, ?) "
            "ON CONFLICT(categoria) DO UPDATE SET limite_mensal = excluded.limite_mensal",
            (categoria, limite_mensal)
        )
    conn.close()


def get_all_limits(db_path: str) -> dict[str, float]:
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT categoria, limite_mensal FROM limites_categoria")
    result = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return result
