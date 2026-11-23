"""Checagens de integridade da gold: o "portão de qualidade" do pipeline.

Cada SELECT de sql/checks/gold.sql é uma checagem que conta violações (esperado: 0). Os
resultados vão para audit.check_log. Se alguma checagem falhar, o pipeline para com erro
antes de gerar a documentação: dado quebrado não segue adiante.
"""

import logging
from datetime import datetime
from pathlib import Path

import duckdb

from src.config import SQL_DIR

log = logging.getLogger(__name__)


class DataCheckError(Exception):
    """Alguma checagem de integridade encontrou violações."""


def setup(con: duckdb.DuckDBPyConnection) -> None:
    """Cria a tabela de log das checagens, se ainda não existir."""
    con.execute("CREATE SCHEMA IF NOT EXISTS audit")
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit.check_log (
            batch_id    INTEGER,
            check_id    VARCHAR,
            description VARCHAR,
            failures    BIGINT,
            checked_at  TIMESTAMP
        )
    """)


def run_checks(
    con: duckdb.DuckDBPyConnection,
    batch_id: int,
    path: Path = SQL_DIR / "checks" / "gold.sql",
) -> None:
    """Roda as checagens, grava o resultado e falha se alguma encontrar violações."""
    setup(con)
    checks_sql = path.read_text(encoding="utf-8").strip().rstrip(";")
    con.execute(
        f"""
        INSERT INTO audit.check_log
        SELECT ?, check_id, description, failures, ?
        FROM ({checks_sql}
        )
        """,
        [batch_id, datetime.now()],
    )
    results = con.execute(
        """
        SELECT check_id, description, failures
        FROM audit.check_log
        WHERE batch_id = ?
        ORDER BY check_id
        """,
        [batch_id],
    ).fetchall()

    failed = []
    for check_id, description, failures in results:
        log.info(
            "  %s  %-6s %6d  %s",
            check_id,
            "ok" if failures == 0 else "FALHOU",
            failures,
            description,
        )
        if failures:
            failed.append(f"{check_id} ({failures})")
    if failed:
        raise DataCheckError("Checagens da gold com violações: " + ", ".join(failed))
