"""Testes da camada silver: vale sempre a versão mais recente de cada registro."""

from datetime import datetime

import pytest

from src import bronze
from src.transform import build_layer

HEADER = (
    "order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,"
    "order_delivered_carrier_date,order_delivered_customer_date,"
    "order_estimated_delivery_date"
)
# O mesmo pedido em dois momentos: primeiro enviado, depois entregue.
SHIPPED = "o1,c1,shipped,2018-01-01 10:00:00,2018-01-01 11:00:00,2018-01-02 09:00:00,,2018-01-20 00:00:00"
DELIVERED = "o1,c1,delivered,2018-01-01 10:00:00,2018-01-01 11:00:00,2018-01-02 09:00:00,2018-01-10 15:00:00,2018-01-20 00:00:00"


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    """Pasta raw temporária; para o teste, o pipeline só conhece a tabela orders."""
    monkeypatch.setattr(bronze, "SOURCES", {"orders": "olist_orders_dataset"})
    return tmp_path


def silver_orders(con):
    return con.execute(
        "SELECT order_id, order_status, order_delivered_customer_date FROM silver.orders"
    ).fetchall()


def test_lote_novo_atualiza_o_pedido_na_silver(con, raw_dir, write_csv):
    write_csv(raw_dir / "olist_orders_dataset.csv", HEADER, [SHIPPED])
    bronze.load_bronze(con, raw_dir)  # lote 1: pedido enviado
    write_csv(raw_dir / "olist_orders_dataset_lote2.csv", HEADER, [DELIVERED])
    bronze.load_bronze(con, raw_dir)  # lote 2: o mesmo pedido, agora entregue

    build_layer(con, "silver", ["orders"])

    # A bronze guarda as duas versões; a silver fica só com a mais recente.
    assert con.execute("SELECT count(*) FROM bronze.orders").fetchone()[0] == 2
    assert silver_orders(con) == [("o1", "delivered", datetime(2018, 1, 10, 15, 0))]


def test_carga_do_zero_com_dois_arquivos_tambem_fica_com_o_mais_recente(
    con, raw_dir, write_csv
):
    # Os dois arquivos já estão na raw e entram no MESMO lote:
    # vale o que vem depois na ordem alfabética do nome.
    write_csv(raw_dir / "olist_orders_dataset.csv", HEADER, [SHIPPED])
    write_csv(raw_dir / "olist_orders_dataset_lote2.csv", HEADER, [DELIVERED])
    bronze.load_bronze(con, raw_dir)

    build_layer(con, "silver", ["orders"])

    assert silver_orders(con) == [("o1", "delivered", datetime(2018, 1, 10, 15, 0))]
