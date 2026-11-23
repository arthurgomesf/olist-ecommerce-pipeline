"""Testes da camada silver: vale sempre a versão mais recente de cada registro."""

from datetime import datetime
from decimal import Decimal

from src import bronze
from src.config import SOURCES
from src.quality import run_quality_rules
from src.transform import build_layer

ORDERS_HEADER = (
    "order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,"
    "order_delivered_carrier_date,order_delivered_customer_date,"
    "order_estimated_delivery_date"
)
# O mesmo pedido em dois momentos: primeiro enviado, depois entregue.
SHIPPED = "o1,c1,shipped,2018-01-01 10:00:00,2018-01-01 11:00:00,2018-01-02 09:00:00,,2018-01-20 00:00:00"
DELIVERED = "o1,c1,delivered,2018-01-01 10:00:00,2018-01-01 11:00:00,2018-01-02 09:00:00,2018-01-10 15:00:00,2018-01-20 00:00:00"

ITEMS_HEADER = "order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value"
ITEM = "o1,1,p1,s1,2018-01-03 10:00:00,20.00,5.00"


def use_only(monkeypatch, *tables):
    """Para o teste, o pipeline passa a conhecer só as tabelas indicadas."""
    monkeypatch.setattr(bronze, "SOURCES", {table: SOURCES[table] for table in tables})


def silver_orders(con):
    return con.execute(
        "SELECT order_id, order_status, order_delivered_customer_date FROM silver.orders"
    ).fetchall()


def test_lote_novo_atualiza_o_pedido_na_silver(con, tmp_path, monkeypatch, write_csv):
    use_only(monkeypatch, "orders")
    write_csv(tmp_path / "olist_orders_dataset.csv", ORDERS_HEADER, [SHIPPED])
    bronze.load_bronze(con, tmp_path)  # lote 1: pedido enviado
    write_csv(tmp_path / "olist_orders_dataset_lote2.csv", ORDERS_HEADER, [DELIVERED])
    bronze.load_bronze(con, tmp_path)  # lote 2: o mesmo pedido, agora entregue

    build_layer(con, "silver", ["orders"])

    # A bronze guarda as duas versões; a silver fica só com a mais recente.
    assert con.execute("SELECT count(*) FROM bronze.orders").fetchone()[0] == 2
    assert silver_orders(con) == [("o1", "delivered", datetime(2018, 1, 10, 15, 0))]


def test_carga_do_zero_com_dois_arquivos_tambem_fica_com_o_mais_recente(
    con, tmp_path, monkeypatch, write_csv
):
    # Os dois arquivos já estão na raw e entram no MESMO lote:
    # vale o que vem depois na ordem alfabética do nome.
    use_only(monkeypatch, "orders")
    write_csv(tmp_path / "olist_orders_dataset.csv", ORDERS_HEADER, [SHIPPED])
    write_csv(tmp_path / "olist_orders_dataset_lote2.csv", ORDERS_HEADER, [DELIVERED])
    bronze.load_bronze(con, tmp_path)

    build_layer(con, "silver", ["orders"])

    assert silver_orders(con) == [("o1", "delivered", datetime(2018, 1, 10, 15, 0))]


def test_preco_absurdo_vira_a_versao_atual_e_e_sinalizado(
    con, tmp_path, monkeypatch, write_csv
):
    use_only(monkeypatch, "orders", "order_items")
    write_csv(tmp_path / "olist_orders_dataset.csv", ORDERS_HEADER, [DELIVERED])
    write_csv(tmp_path / "olist_order_items_dataset.csv", ITEMS_HEADER, [ITEM])
    bronze.load_bronze(con, tmp_path)  # lote 1: item com preço normal (R$ 20)

    absurd = ITEM.replace("20.00", "999999.00")
    write_csv(tmp_path / "olist_order_items_dataset_lote2.csv", ITEMS_HEADER, [absurd])
    batch_id = bronze.load_bronze(con, tmp_path)  # lote 2: o mesmo item a R$ 999.999

    build_layer(con, "silver", ["orders", "order_items"])
    run_quality_rules(con, batch_id, ["order_items"])

    # A silver fica com a versão mais recente (o preço novo), marcada como suspeita...
    assert con.execute(
        "SELECT price, dq_price_out_of_range FROM silver.order_items"
    ).fetchall() == [(Decimal("999999.00"), True)]
    # ...e a regra de qualidade registra o alerta no log daquele lote.
    (flagged,) = con.execute(
        "SELECT rows_affected FROM audit.quality_log WHERE rule_id = 'ITM-03' AND batch_id = ?",
        [batch_id],
    ).fetchone()
    assert flagged == 1
