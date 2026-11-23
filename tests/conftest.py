"""Fixtures compartilhadas por todos os testes (o pytest carrega este arquivo sozinho)."""

import duckdb
import pytest


@pytest.fixture
def con():
    """Banco DuckDB em memória, descartado ao fim de cada teste."""
    with duckdb.connect() as connection:
        yield connection


@pytest.fixture
def write_csv():
    """Função para criar CSVs pequenos: write_csv(caminho, cabeçalho, linhas)."""

    def _write_csv(path, header, rows):
        path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")

    return _write_csv
