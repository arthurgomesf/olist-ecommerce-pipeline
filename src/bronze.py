"""Camada bronze: carga incremental e fiel dos CSVs da raw para o DuckDB.

Regras da camada:
- Só recebe inserções (append-only): nenhuma linha é alterada ou apagada.
- Todas as colunas entram como texto, exatamente como estão no arquivo. Converter
  tipos (datas, números) é uma decisão explícita da camada silver.
- Cada linha ganha colunas de controle:
    _row_hash     "impressão digital" (md5) do conteúdo da linha
    _batch_id     número da execução (lote) que inseriu a linha
    _source_file  nome do arquivo de origem
    _ingested_at  momento da carga
- Só entram linhas cujo _row_hash ainda não existe na tabela. Assim, rodar o pipeline
  de novo não duplica nada, e um arquivo novo acrescenta apenas o que é novo ou mudou.
"""

import logging
from datetime import datetime
from pathlib import Path

import duckdb

from src.config import RAW_DIR, SOURCES

log = logging.getLogger(__name__)


def setup(con: duckdb.DuckDBPyConnection) -> None:
    """Cria os schemas e a tabela de log de cargas, se ainda não existirem."""
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("CREATE SCHEMA IF NOT EXISTS audit")
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit.load_log (
            batch_id      INTEGER,
            table_name    VARCHAR,
            source_file   VARCHAR,
            rows_read     BIGINT,
            rows_inserted BIGINT,
            loaded_at     TIMESTAMP
        )
    """)


def next_batch_id(con: duckdb.DuckDBPyConnection) -> int:
    """Número do próximo lote: 1 na primeira carga; depois, o último + 1."""
    (last_batch,) = con.execute("SELECT max(batch_id) FROM audit.load_log").fetchone()
    return (last_batch or 0) + 1


def find_source_files(raw_dir: Path = RAW_DIR) -> dict[str, list[Path]]:
    """Lista os arquivos de cada tabela. Falha logo se alguma tabela não tiver arquivo."""
    files = {
        table: sorted(raw_dir.glob(f"{prefix}*.csv"))
        for table, prefix in SOURCES.items()
    }
    missing = [f"{SOURCES[table]}*.csv" for table, paths in files.items() if not paths]
    if missing:
        raise FileNotFoundError(
            f"Arquivos não encontrados em {raw_dir}: {', '.join(missing)}. "
            "Baixe o dataset da Olist no Kaggle e extraia os CSVs nessa pasta (ver README)."
        )
    return files


def load_file(
    con: duckdb.DuckDBPyConnection, table: str, csv_path: Path, batch_id: int
) -> tuple[int, int]:
    """Carrega um CSV em bronze.<table>. Retorna (linhas lidas, linhas inseridas)."""
    target = f"bronze.{table}"
    path = csv_path.as_posix().replace("'", "''")

    # Transação: ou o arquivo entra inteiro (dados + log), ou nada entra.
    con.begin()
    try:
        # 1) Área de preparação (staging): lê o arquivo uma única vez, tudo como texto,
        #    e calcula as colunas de controle. src::VARCHAR transforma a linha inteira em
        #    texto (incluindo quais colunas são nulas), e o md5 vira a impressão digital.
        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE staging AS
            SELECT
                src.*,
                md5(src::VARCHAR) AS _row_hash,
                ?::INTEGER        AS _batch_id,
                ?::VARCHAR        AS _source_file,
                ?::TIMESTAMP      AS _ingested_at
            FROM read_csv('{path}', header = true, delim = ',', quote = '"',
                          all_varchar = true) AS src
            """,
            [batch_id, csv_path.name, datetime.now()],
        )
        (rows_read,) = con.execute("SELECT count(*) FROM staging").fetchone()

        # 2) Na primeira carga, cria a tabela bronze com a mesma estrutura (sem linhas).
        con.execute(
            f"CREATE TABLE IF NOT EXISTS {target} AS SELECT * FROM staging LIMIT 0"
        )

        # 3) Proteção contra mudança de layout: se o arquivo novo tiver colunas
        #    diferentes das que já estão na bronze, a carga para com erro claro.
        if con.table("staging").columns != con.table(target).columns:
            raise ValueError(
                f"Colunas de {csv_path.name} diferem das de {target}. "
                "Mudança de layout precisa ser tratada antes da carga."
            )

        # 4) Insere só as linhas cuja impressão digital ainda não existe na bronze.
        (rows_inserted,) = con.execute(f"""
            INSERT INTO {target}
            SELECT * FROM staging AS new
            WHERE NOT EXISTS (
                SELECT 1 FROM {target} AS old WHERE old._row_hash = new._row_hash
            )
        """).fetchone()

        # 5) Registra o lote no log de cargas.
        con.execute(
            "INSERT INTO audit.load_log VALUES (?, ?, ?, ?, ?, ?)",
            [batch_id, table, csv_path.name, rows_read, rows_inserted, datetime.now()],
        )
        con.execute("DROP TABLE staging")
        con.commit()
    except Exception:
        con.rollback()
        raise

    return rows_read, rows_inserted


def load_bronze(con: duckdb.DuckDBPyConnection, raw_dir: Path = RAW_DIR) -> int:
    """Carrega todos os arquivos da raw na bronze, como um novo lote. Retorna o batch_id."""
    files = find_source_files(raw_dir)  # valida tudo antes de começar a carregar
    setup(con)
    batch_id = next_batch_id(con)
    log.info("Bronze: iniciando lote %d", batch_id)

    for table, paths in files.items():
        for csv_path in paths:
            rows_read, rows_inserted = load_file(con, table, csv_path, batch_id)
            log.info(
                "  bronze.%-22s %-42s lidas=%9d  inseridas=%9d",
                table,
                csv_path.name,
                rows_read,
                rows_inserted,
            )
    return batch_id
