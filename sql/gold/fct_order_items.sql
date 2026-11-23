-- gold.fct_order_items
-- Grão: 1 linha por item de pedido (order_id + order_item_id).
-- É o fato de receita: permite somar valores por produto, categoria e vendedor. A data e o
-- status do pedido são copiados para cá, para que análises de receita nunca precisem
-- juntar dois fatos.

CREATE OR REPLACE TABLE gold.fct_order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    o.customer_id,
    o.order_purchase_timestamp::DATE  AS order_purchase_date,  -- liga com dim_date
    o.order_status,
    is_completed_sale(o.order_status) AS is_completed_sale,  -- entra na receita
    i.price,
    i.freight_value,
    i.dq_price_out_of_range
FROM silver.order_items AS i
LEFT JOIN silver.orders AS o USING (order_id);
