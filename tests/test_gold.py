"""Testes da gold: as métricas de entrega do fct_orders."""

from src import bronze
from src.config import SOURCES
from src.transform import build_layer

ORDERS_HEADER = (
    "order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,"
    "order_delivered_carrier_date,order_delivered_customer_date,"
    "order_estimated_delivery_date"
)
# Tabelas que o fct_orders consulta; aqui entram vazias (só o cabeçalho).
EMPTY_TABLES = {
    "order_items": (
        "order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value"
    ),
    "order_payments": (
        "order_id,payment_sequential,payment_type,payment_installments,payment_value"
    ),
    "order_reviews": (
        "review_id,order_id,review_score,review_comment_title,review_comment_message,"
        "review_creation_date,review_answer_timestamp"
    ),
}


def test_atraso_e_medido_por_data_e_nao_por_horario(
    con, tmp_path, monkeypatch, write_csv
):
    tables = ["orders", *EMPTY_TABLES]
    monkeypatch.setattr(bronze, "SOURCES", {table: SOURCES[table] for table in tables})
    orders = [
        # Entregue às 15h do PRÓPRIO dia prometido: não está atrasado.
        (
            "o1,c1,delivered,2018-01-01 10:00:00,2018-01-01 11:00:00,"
            "2018-01-03 09:00:00,2018-01-20 15:00:00,2018-01-20 00:00:00"
        ),
        # Entregue 2 dias depois do prometido: atrasado.
        (
            "o2,c2,delivered,2018-01-01 10:00:00,2018-01-01 11:00:00,"
            "2018-01-03 09:00:00,2018-01-22 08:00:00,2018-01-20 00:00:00"
        ),
        # Ainda em trânsito: sem métricas de entrega.
        (
            "o3,c3,shipped,2018-01-01 10:00:00,2018-01-01 11:00:00,"
            "2018-01-03 09:00:00,,2018-01-20 00:00:00"
        ),
    ]
    write_csv(tmp_path / "olist_orders_dataset.csv", ORDERS_HEADER, orders)
    for table, header in EMPTY_TABLES.items():
        write_csv(tmp_path / f"{SOURCES[table]}.csv", header, [])
    bronze.load_bronze(con, tmp_path)

    build_layer(con, "silver", tables)
    build_layer(con, "gold", ["fct_orders"])

    assert con.execute("""
        SELECT order_id, delivery_days, estimated_days, delay_days, is_late
        FROM gold.fct_orders
        ORDER BY order_id
    """).fetchall() == [
        ("o1", 19, 19, 0, False),
        ("o2", 21, 19, 2, True),
        ("o3", None, None, None, None),
    ]
