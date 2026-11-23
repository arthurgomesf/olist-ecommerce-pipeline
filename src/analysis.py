"""Consultas das análises: lê sql/analysis/<nome>.sql e devolve um DataFrame.

Usado pelo notebook e pelo dashboard, para que os dois mostrem exatamente os mesmos números.
O banco é aberto só para leitura e fechado logo após cada consulta: assim o pipeline pode
reescrever o arquivo sem conflito (o DuckDB não deixa um processo escrever enquanto outro
está com o arquivo aberto).
"""

import duckdb
import pandas as pd

from src.config import DB_PATH, SQL_DIR


def run_query(name: str) -> pd.DataFrame:
    """Executa sql/analysis/<name>.sql sobre o Data Warehouse e devolve o resultado."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} não existe. Rode o pipeline primeiro: python -m src.pipeline"
        )
    sql = (SQL_DIR / "analysis" / f"{name}.sql").read_text(encoding="utf-8")
    with duckdb.connect(DB_PATH, read_only=True) as con:
        return con.sql(sql).df()
