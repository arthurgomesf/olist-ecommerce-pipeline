"""Registro das regras de qualidade.

Cada arquivo sql/quality/<tabela>.sql lista as regras da tabela (uma por SELECT) com a
quantidade de linhas afetadas. O resultado de cada execução é gravado em
audit.quality_log, que depois alimenta a documentação (os números não são digitados à mão).
"""

import logging
from datetime import datetime

import duckdb

from src.config import SQL_DIR

log = logging.getLogger(__name__)


def setup(con: duckdb.DuckDBPyConnection) -> None:
    """Cria a tabela de log das regras, se ainda não existir."""
    con.execute("CREATE SCHEMA IF NOT EXISTS audit")
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit.quality_log (
            batch_id      INTEGER,
            rule_id       VARCHAR,
            table_name    VARCHAR,
            rule          VARCHAR,
            action        VARCHAR,
            reason        VARCHAR,
            rows_affected BIGINT,
            checked_at    TIMESTAMP
        )
    """)


def run_quality_rules(
    con: duckdb.DuckDBPyConnection, batch_id: int, tables: list[str]
) -> None:
    """Calcula as regras de cada tabela e grava o resultado no log, ligado ao lote."""
    setup(con)
    for table in tables:
        rules_sql = (SQL_DIR / "quality" / f"{table}.sql").read_text(encoding="utf-8")
        rules_sql = rules_sql.strip().rstrip(";")  # vai dentro de um FROM (...)
        con.execute(
            f"""
            INSERT INTO audit.quality_log
            SELECT ?, rule_id, table_name, rule, action, reason, rows_affected, ?
            FROM ({rules_sql}
            )
            """,
            [batch_id, datetime.now()],
        )
        results = con.execute(
            """
            SELECT rule_id, action, rows_affected, rule
            FROM audit.quality_log
            WHERE batch_id = ? AND table_name = ?
            ORDER BY rule_id
            """,
            [batch_id, table],
        ).fetchall()
        for rule_id, action, rows_affected, rule in results:
            log.info("  %s  %-9s %9d  %s", rule_id, action, rows_affected, rule)
