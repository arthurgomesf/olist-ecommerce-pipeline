"""Testes da camada silver: vale sempre a versão mais recente de cada registro."""

from datetime import datetime
from decimal import Decimal

import pytest

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

GEO_HEADER = (
    "geolocation_zip_code_prefix,geolocation_lat,geolocation_lng,"
    "geolocation_city,geolocation_state"
)
GEO_OTHER_ZIP = "99999,-10.0,-50.0,outra cidade,TO"  # um CEP que nenhum vendedor usa
SELLERS_HEADER = "seller_id,seller_zip_code_prefix,seller_city,seller_state"

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


def test_geolocalizacao_consolida_um_cep_por_linha(
    con, tmp_path, monkeypatch, write_csv
):
    use_only(monkeypatch, "geolocation")
    points = [
        "01001,-23.55,-46.63,são paulo,SP",
        "01001,-23.55,-46.63,são paulo,SP",  # duplicata exata
        "01001,-23.56,-46.64,sao paulo,SP",
        "01001,38.27,-7.80,sao paulo,SP",  # cai em Portugal: erro de geocodificação
        "53990,-3.85,-32.42,fernando de noronha,PE",  # ilha: precisa ficar
    ]
    write_csv(tmp_path / "olist_geolocation_dataset.csv", GEO_HEADER, points)
    bronze.load_bronze(con, tmp_path)

    build_layer(con, "silver", ["geolocation"])

    rows = con.execute("""
        SELECT geolocation_zip_code_prefix, geolocation_lat, geolocation_lng,
               geolocation_city, geolocation_state, points
        FROM silver.geolocation
        ORDER BY 1
    """).fetchall()
    assert rows == [
        ("01001", pytest.approx(-23.555), pytest.approx(-46.635), "sao paulo", "SP", 2),
        ("53990", -3.85, -32.42, "fernando de noronha", "PE", 1),
    ]


def test_cidade_do_vendedor_e_padronizada(con, tmp_path, monkeypatch, write_csv):
    use_only(monkeypatch, "geolocation", "sellers")
    # Base de CEPs sem os CEPs dos vendedores: aqui testamos só a limpeza do texto.
    write_csv(tmp_path / "olist_geolocation_dataset.csv", GEO_HEADER, [GEO_OTHER_ZIP])
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
    write_csv(tmp_path / "olist_sellers_dataset.csv", SELLERS_HEADER, rows)
    bronze.load_bronze(con, tmp_path)

    build_layer(con, "silver", ["geolocation", "sellers"])

    result = dict(
        con.execute("SELECT seller_id, seller_city FROM silver.sellers").fetchall()
    )
    assert result == {seller_id: expected for seller_id, _, _, expected in cases}


def test_localizacao_do_vendedor_segue_o_cep(con, tmp_path, monkeypatch, write_csv):
    use_only(monkeypatch, "geolocation", "sellers")
    points = [
        "31570,-19.86,-43.92,belo horizonte,MG",
        "09726,-23.70,-46.55,são bernardo do campo,SP",
    ]
    write_csv(tmp_path / "olist_geolocation_dataset.csv", GEO_HEADER, points)
    sellers = [
        "s1,31570,belo horizonte,SP",  # UF digitada errada: o CEP é de MG
        "s2,09726,sbc/sp,SP",  # abreviação: vira a cidade do CEP
        "s3,09726,sao bernardo do campo,SP",  # já está certo: não muda
    ]
    write_csv(tmp_path / "olist_sellers_dataset.csv", SELLERS_HEADER, sellers)
    bronze.load_bronze(con, tmp_path)

    build_layer(con, "silver", ["geolocation", "sellers"])

    assert con.execute("""
        SELECT seller_id, seller_city, seller_state, dq_state_from_zip, dq_city_from_zip
        FROM silver.sellers
        ORDER BY seller_id
    """).fetchall() == [
        ("s1", "belo horizonte", "MG", True, False),
        ("s2", "sao bernardo do campo", "SP", False, True),
        ("s3", "sao bernardo do campo", "SP", False, False),
    ]


def test_categoria_traduzida_com_fallback_manual_e_rotulo_para_nulo(
    con, tmp_path, monkeypatch, write_csv
):
    use_only(monkeypatch, "products", "category_translation")
    header = (
        "product_id,product_category_name,product_name_lenght,product_description_lenght,"
        "product_photos_qty,product_weight_g,product_length_cm,product_height_cm,"
        "product_width_cm"
    )
    products = [
        "p1,beleza_saude,40,287,1,225,16,10,14",  # tem tradução oficial
        "p2,pc_gamer,40,287,1,225,16,10,14",  # só tem tradução manual
        "p3,,,,,0,16,10,14",  # sem categoria e com peso zero
    ]
    write_csv(tmp_path / "olist_products_dataset.csv", header, products)
    write_csv(
        tmp_path / "product_category_name_translation.csv",
        "product_category_name,product_category_name_english",
        ["beleza_saude,health_beauty"],
    )
    bronze.load_bronze(con, tmp_path)

    build_layer(con, "silver", ["products"])

    assert con.execute("""
        SELECT product_id, product_category_name, product_category_name_en, product_weight_g
        FROM silver.products
        ORDER BY product_id
    """).fetchall() == [
        ("p1", "beleza_saude", "health_beauty", 225),
        ("p2", "pc_gamer", "gaming_pc", 225),
        ("p3", "sem_categoria", "unknown", None),
    ]
