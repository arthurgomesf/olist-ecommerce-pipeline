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

REVIEWS_HEADER = (
    "review_id,order_id,review_score,review_comment_title,review_comment_message,"
    "review_creation_date,review_answer_timestamp"
)


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


def test_pedido_com_duas_avaliacoes_fica_com_a_respondida_por_ultimo(
    con, tmp_path, monkeypatch, write_csv
):
    use_only(monkeypatch, "order_reviews")
    # A mais recente vem primeiro no arquivo: a escolha não pode depender da posição.
    reviews = [
        "r2,o1,5,,Chegou tudo certo,2018-01-15 00:00:00,2018-01-16 09:00:00",
        "r1,o1,1,,Demorou muito,2018-01-11 00:00:00,2018-01-12 10:00:00",
    ]
    write_csv(tmp_path / "olist_order_reviews_dataset.csv", REVIEWS_HEADER, reviews)
    bronze.load_bronze(con, tmp_path)

    build_layer(con, "silver", ["order_reviews"])

    assert con.execute(
        "SELECT order_id, review_id, review_score FROM silver.order_reviews"
    ).fetchall() == [("o1", "r2", 5)]


def test_cidade_do_vendedor_e_padronizada(con, tmp_path, monkeypatch, write_csv):
    use_only(monkeypatch, "sellers")
    # (seller_id, cidade como veio, UF, cidade esperada na silver) - casos reais da base
    cases = [
        ("s1", "sao paulo / sao paulo", "SP", "sao paulo"),
        ("s2", "lages - sc", "SC", "lages"),
        ("s3", "andira-pr", "PR", "andira"),
        ("s4", "mogi-guacu", "SP", "mogi-guacu"),  # hífen do nome não pode sumir
        ("s5", "são  paulo", "SP", "sao paulo"),  # acento + espaço duplo
        ("s6", "santa barbara d´oeste", "SP", "santa barbara d'oeste"),
        ("s7", '"novo hamburgo, rio grande do sul, brasil"', "RS", "novo hamburgo"),
        ("s8", "04482255", "RJ", None),  # CEP no lugar da cidade
        ("s9", "vendas@creditparts.com.br", "PR", None),  # e-mail no lugar da cidade
    ]
    rows = [f"{seller_id},01000,{city},{uf}" for seller_id, city, uf, _ in cases]
    header = "seller_id,seller_zip_code_prefix,seller_city,seller_state"
    write_csv(tmp_path / "olist_sellers_dataset.csv", header, rows)
    bronze.load_bronze(con, tmp_path)

    build_layer(con, "silver", ["sellers"])

    result = dict(
        con.execute("SELECT seller_id, seller_city FROM silver.sellers").fetchall()
    )
    assert result == {seller_id: expected for seller_id, _, _, expected in cases}
