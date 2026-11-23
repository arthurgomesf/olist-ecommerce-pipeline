"""Gera docs/data_quality.md a partir do log de regras de qualidade.

O arquivo é reescrito a cada execução com as regras e contagens do lote mais recente, então
os números da documentação nunca são digitados à mão. Ele não traz data nem número do lote:
com os mesmos dados, o arquivo sai idêntico (e o Git não acusa mudança à toa).
"""

import logging
from pathlib import Path

import duckdb

from src.config import DOCS_DIR, SILVER_TABLES

log = logging.getLogger(__name__)

ACTIONS = {
    "remover": "a linha sai da silver (continua guardada na bronze)",
    "corrigir": "o valor é ajustado; a correção fica marcada numa flag `dq_*`",
    "sinalizar": "a linha fica, marcada com uma flag `dq_*` para as análises decidirem",
    "manter": "nada muda; o caso fica registrado para transparência",
}


def fmt(number: int) -> str:
    """Formata números no padrão brasileiro: 261831 -> '261.831'."""
    return f"{number:,}".replace(",", ".")


def write_quality_report(
    con: duckdb.DuckDBPyConnection,
    batch_id: int,
    path: Path = DOCS_DIR / "data_quality.md",
) -> None:
    """Escreve o relatório Markdown com volumes por tabela e todas as regras do lote."""
    lines = [
        "# Regras de qualidade",
        "",
        "> Arquivo gerado automaticamente pelo pipeline (`python -m src.pipeline`) a partir",
        "> da tabela `audit.quality_log`. Não edite à mão: as contagens são as da última execução.",
        "",
        "## Como ler",
        "",
        "| Ação | O que significa |",
        "|---|---|",
        *[f"| {action} | {meaning} |" for action, meaning in ACTIONS.items()],
        "",
        "## Volumes por tabela",
        "",
        "| Tabela | Linhas na bronze | Linhas na silver |",
        "|---|---:|---:|",
    ]
    for table in SILVER_TABLES:
        (bronze_rows,) = con.execute(f"SELECT count(*) FROM bronze.{table}").fetchone()
        (silver_rows,) = con.execute(f"SELECT count(*) FROM silver.{table}").fetchone()
        lines.append(f"| {table} | {fmt(bronze_rows)} | {fmt(silver_rows)} |")

    lines += ["", "## Regras por tabela"]
    for table in SILVER_TABLES:
        rules = con.execute(
            """
            SELECT rule_id, rule, action, rows_affected, reason
            FROM audit.quality_log
            WHERE batch_id = ? AND table_name = ?
            ORDER BY rule_id
            """,
            [batch_id, table],
        ).fetchall()
        lines += [
            "",
            f"### {table}",
            "",
            "| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |",
            "|---|---|---|---:|---|",
        ]
        for rule_id, rule, action, rows_affected, reason in rules:
            lines.append(
                f"| {rule_id} | {rule} | {action} | {fmt(rows_affected)} | {reason} |"
            )

    checks = con.execute(
        """
        SELECT check_id, description, failures
        FROM audit.check_log
        WHERE batch_id = ?
        ORDER BY check_id
        """,
        [batch_id],
    ).fetchall()
    lines += [
        "",
        "## Checagens de integridade da gold",
        "",
        "Rodam a cada execução, depois da gold. Se alguma encontrar violações, o pipeline para",
        "com erro e esta documentação não é gerada.",
        "",
        "| Checagem | O que é verificado | Violações |",
        "|---|---|---:|",
        *[
            f"| {check_id} | {description} | {fmt(failures)} |"
            for check_id, description, failures in checks
        ],
    ]

    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    log.info("  %s atualizado", path.relative_to(path.parents[1]).as_posix())
