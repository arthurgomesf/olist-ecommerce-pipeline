"""Orquestrador do pipeline. Uso, a partir da raiz do repositório:

    python -m src.pipeline

Roda as etapas em ordem (por enquanto: bronze) sobre o arquivo warehouse/olist.duckdb.
"""

import logging
import sys
import time

import duckdb

from src.bronze import load_bronze
from src.config import DB_PATH, WAREHOUSE_DIR

log = logging.getLogger("pipeline")


def connect() -> duckdb.DuckDBPyConnection:
    """Abre (ou cria) o Data Warehouse. Falha com mensagem clara se o arquivo estiver em uso."""
    WAREHOUSE_DIR.mkdir(exist_ok=True)
    try:
        return duckdb.connect(DB_PATH)
    except duckdb.IOException as error:
        # O DuckDB permite um único processo escrevendo no arquivo. Se o notebook, o
        # dashboard ou outro terminal estiver com o banco aberto, a conexão é recusada.
        raise SystemExit(
            f"Não foi possível abrir {DB_PATH.name}: o arquivo está em uso por outro programa "
            "(notebook, dashboard ou outro terminal). Feche-o e rode o pipeline de novo."
        ) from error


def run() -> None:
    """Executa todas as etapas do pipeline, registrando o tempo de cada uma."""
    start = time.perf_counter()
    with connect() as con:
        step = time.perf_counter()
        batch_id = load_bronze(con)
        log.info("Bronze concluída em %.1fs", time.perf_counter() - step)

    log.info(
        "Pipeline concluído: lote %d em %.1fs", batch_id, time.perf_counter() - start
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        run()
    except FileNotFoundError as error:  # CSVs ausentes: mensagem limpa, sem traceback
        log.error("%s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
