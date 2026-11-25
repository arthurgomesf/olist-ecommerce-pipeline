"""Orquestrador do pipeline. Uso, a partir da raiz do repositório:

    python -m src.pipeline

Roda as etapas em ordem sobre o arquivo warehouse/olist.duckdb:
bronze (carga incremental) -> silver (limpeza) -> regras de qualidade -> gold (modelo
estrela) -> checagens da gold -> documentação. A gold e as checagens rodam numa transação:
se alguma checagem falhar, a gold nova é desfeita, a anterior continua valendo e o
pipeline para com erro.
"""

import logging
import sys
import time
from contextlib import contextmanager

import duckdb

from src.bronze import load_bronze
from src.checks import DataCheckError, run_checks
from src.config import DB_PATH, GOLD_TABLES, SILVER_TABLES, WAREHOUSE_DIR
from src.docs import write_quality_report
from src.quality import run_quality_rules
from src.transform import build_layer

log = logging.getLogger("pipeline")


@contextmanager
def step(name: str):
    """Mede e registra no log quanto tempo uma etapa levou."""
    start = time.perf_counter()
    yield
    log.info("Etapa '%s' concluída em %.1fs", name, time.perf_counter() - start)


@contextmanager
def transaction(con: duckdb.DuckDBPyConnection):
    """Tudo dentro do bloco vale junto: se algo falhar, nada é gravado (rollback)."""
    con.begin()
    try:
        yield
    except BaseException:
        con.rollback()
        raise
    con.commit()


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
        with step("bronze"):
            batch_id = load_bronze(con)
        with step("silver"):
            build_layer(con, "silver", SILVER_TABLES)
        with step("regras de qualidade"):
            run_quality_rules(con, batch_id, SILVER_TABLES)
        # A gold nova só é publicada se passar nas checagens; senão, fica a anterior.
        with transaction(con):
            with step("gold"):
                build_layer(con, "gold", GOLD_TABLES)
            with step("checagens da gold"):
                run_checks(con, batch_id)
        with step("documentação"):
            write_quality_report(con, batch_id)

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
    # Erros esperados ganham mensagem limpa, sem traceback: CSVs ausentes ou dado quebrado.
    except FileNotFoundError as error:
        log.error("%s", error)
        sys.exit(1)
    except DataCheckError as error:
        log.error("%s. A gold nova foi descartada; a anterior continua valendo.", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
