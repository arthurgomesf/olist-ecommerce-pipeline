"""Checagens de integridade da gold: o "portão de qualidade" do pipeline.

Cada SELECT de sql/checks/gold.sql é uma checagem que conta violações (esperado: 0). Os
resultados vão para audit.check_log. No pipeline, a gold é recriada e conferida dentro de
uma transação: se alguma checagem falhar, a gold nova é desfeita (a anterior continua
valendo) e o pipeline para com erro antes de gerar a documentação.
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
    """Roda as checagens, grava o resultado e falha se alguma encontrar violações.

    As checagens usam a conexão recebida, que enxerga a gold nova mesmo antes de ela ser
    confirmada. Já o log é gravado por uma conexão separada (cursor), fora da transação do
    pipeline: assim o registro da falha fica salvo mesmo quando a gold nova é desfeita.
    """
    checks_sql = path.read_text(encoding="utf-8").strip().rstrip(";")
    results = con.execute(
        f"""
        SELECT check_id, description, failures
        FROM ({checks_sql}
        )
        ORDER BY check_id
        """
    ).fetchall()

    checked_at = datetime.now()
    with con.cursor() as log_con:
        setup(log_con)
        log_con.executemany(
            "INSERT INTO audit.check_log VALUES (?, ?, ?, ?, ?)",
            [(batch_id, *result, checked_at) for result in results],
        )

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
