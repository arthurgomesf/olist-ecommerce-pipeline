"""Testes da carga incremental da bronze.

Cada teste roda num banco em memória e numa pasta raw temporária, com um CSV pequeno
de order_items criado pelo próprio teste. Nada toca nos dados reais nem no warehouse/.
"""

import duckdb
import pytest

from src import bronze

HEADER = "order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value"
ROWS = [
    "o1,1,p1,s1,2018-01-01 10:00:00,10.00,5.00",
    "o2,1,p2,s1,2018-01-02 10:00:00,20.00,5.00",
    "o3,1,p3,s2,2018-01-03 10:00:00,30.00,5.00",
]


def write_csv(path, header, rows):
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def count_rows(con):
    return con.execute("SELECT count(*) FROM bronze.order_items").fetchone()[0]


@pytest.fixture
def con():
    """Banco DuckDB em memória, descartado ao fim de cada teste."""
    with duckdb.connect() as connection:
        yield connection


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    """Pasta raw temporária com um único arquivo de order_items (3 linhas).

    Para o teste, o pipeline passa a conhecer só a tabela order_items.
    """
    monkeypatch.setattr(bronze, "SOURCES", {"order_items": "olist_order_items_dataset"})
    write_csv(tmp_path / "olist_order_items_dataset.csv", HEADER, ROWS)
    return tmp_path


def test_rodar_de_novo_nao_duplica(con, raw_dir):
    bronze.load_bronze(con, raw_dir)
    bronze.load_bronze(con, raw_dir)

    assert count_rows(con) == 3
    log = con.execute(
        "SELECT batch_id, rows_inserted FROM audit.load_log ORDER BY batch_id"
    ).fetchall()
    assert log == [(1, 3), (2, 0)]


def test_arquivo_novo_insere_so_a_linha_alterada(con, raw_dir):
    bronze.load_bronze(con, raw_dir)

    # Lote 2: chega um arquivo novo com as mesmas 3 linhas, mas o preço do item o2
    # foi alterado para um valor absurdo.
    changed = [ROWS[0], ROWS[1].replace("20.00", "999999.00"), ROWS[2]]
    write_csv(raw_dir / "olist_order_items_dataset_lote2.csv", HEADER, changed)
    bronze.load_bronze(con, raw_dir)

    assert count_rows(con) == 4  # 3 originais + só a nova versão do item o2
    versions = con.execute("""
        SELECT price, _batch_id, _source_file
        FROM bronze.order_items
        WHERE order_id = 'o2'
        ORDER BY _batch_id
    """).fetchall()
    assert versions == [
        ("20.00", 1, "olist_order_items_dataset.csv"),
        ("999999.00", 2, "olist_order_items_dataset_lote2.csv"),
    ]


def test_arquivo_com_colunas_diferentes_e_recusado(con, raw_dir):
    bronze.load_bronze(con, raw_dir)

    # Lote 2: o arquivo novo renomeou a coluna price -> a carga deve parar.
    other_header = HEADER.replace("price", "unit_price")
    write_csv(raw_dir / "olist_order_items_dataset_lote2.csv", other_header, ROWS)
    with pytest.raises(ValueError, match="diferem"):
        bronze.load_bronze(con, raw_dir)

    assert count_rows(con) == 3  # nada do arquivo recusado entrou (transação desfeita)
    loaded_files = [
        row[0]
        for row in con.execute("SELECT source_file FROM audit.load_log").fetchall()
    ]
    assert "olist_order_items_dataset_lote2.csv" not in loaded_files


def test_duplicatas_dentro_do_mesmo_arquivo_sao_mantidas(con, tmp_path, monkeypatch):
    # A bronze é cópia fiel: se o próprio arquivo repete uma linha, as duas entram.
    # Quem remove duplicatas é a camada silver (ex.: geolocalização).
    monkeypatch.setattr(bronze, "SOURCES", {"order_items": "olist_order_items_dataset"})
    write_csv(tmp_path / "olist_order_items_dataset.csv", HEADER, [ROWS[0], ROWS[0]])

    bronze.load_bronze(con, tmp_path)

    assert count_rows(con) == 2
