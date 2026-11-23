"""Executa as transformações em SQL de uma camada (silver ou gold).

Cada tabela é um arquivo sql/<camada>/<tabela>.sql com um CREATE OR REPLACE TABLE.
A camada é recalculada a partir da camada anterior a cada execução, então o resultado
é sempre consistente com tudo o que já foi carregado na bronze.
"""

import logging

import duckdb

from src.config import SQL_DIR

log = logging.getLogger(__name__)


def build_layer(con: duckdb.DuckDBPyConnection, layer: str, tables: list[str]) -> None:
    """Roda sql/<layer>/<tabela>.sql para cada tabela, na ordem dada."""
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {layer}")
    for table in tables:
        sql = (SQL_DIR / layer / f"{table}.sql").read_text(encoding="utf-8")
        con.execute(sql)
        (rows,) = con.execute(f"SELECT count(*) FROM {layer}.{table}").fetchone()
        log.info("  %s.%-22s linhas=%9d", layer, table, rows)
