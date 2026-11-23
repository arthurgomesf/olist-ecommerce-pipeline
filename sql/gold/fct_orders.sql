-- gold.fct_orders
-- Grão: 1 linha por pedido (order_id). É a tabela derivada com as métricas de entrega.
-- Valores do pedido (itens, frete, pagamento, nota) são agregados AQUI, no grão do pedido,
-- para não se repetirem em cada item e serem somados em dobro (fan-out).
--
-- Métricas de entrega (preenchidas só para pedidos entregues com data de entrega):
--   delivery_days   dias corridos entre a compra e a entrega ao cliente
--   estimated_days  dias corridos entre a compra e a data prometida
--   delay_days      entrega - data prometida, em dias (positivo = atraso; negativo = antes)
--   is_late         entregue DEPOIS do dia prometido. A comparação é por DATA: a data
--                   prometida não tem hora (00:00), então comparar com o horário da entrega
--                   marcaria como atrasada uma entrega feita no próprio dia prometido.

CREATE OR REPLACE TABLE gold.fct_orders AS
WITH items AS (
    SELECT
        order_id,
        count(*)            AS item_count,
        sum(price)          AS items_value,
        sum(freight_value)  AS freight_value
    FROM silver.order_items
    GROUP BY order_id
),

payments AS (
    SELECT order_id, sum(payment_value) AS payment_value
    FROM silver.order_payments
    GROUP BY order_id
),

base AS (
    SELECT
        o.*,
        (o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL)
            AS is_delivered
    FROM silver.orders AS o
)

SELECT
    b.order_id,
    b.customer_id,
    b.order_purchase_timestamp::DATE           AS order_purchase_date,  -- liga com dim_date
    b.order_status,
    is_completed_sale(b.order_status)          AS is_completed_sale,  -- entra na receita
    b.is_delivered,

    b.order_purchase_timestamp,
    b.order_approved_at,
    b.order_delivered_carrier_date,
    b.order_delivered_customer_date,
    b.order_estimated_delivery_date,

    coalesce(i.item_count, 0)                  AS item_count,
    coalesce(i.items_value, 0)                 AS items_value,
    coalesce(i.freight_value, 0)               AS freight_value,
    p.payment_value,                           -- nulo = pedido sem pagamento registrado
    r.review_score,                            -- nulo = pedido sem avaliação

    CASE WHEN b.is_delivered THEN date_diff('day', b.order_purchase_timestamp::DATE,
                                            b.order_delivered_customer_date::DATE) END
        AS delivery_days,
    CASE WHEN b.is_delivered THEN date_diff('day', b.order_purchase_timestamp::DATE,
                                            b.order_estimated_delivery_date) END
        AS estimated_days,
    CASE WHEN b.is_delivered THEN date_diff('day', b.order_estimated_delivery_date,
                                            b.order_delivered_customer_date::DATE) END
        AS delay_days,
    CASE WHEN b.is_delivered THEN b.order_delivered_customer_date::DATE
                                  > b.order_estimated_delivery_date END
        AS is_late,

    (b.dq_delivered_without_date OR b.dq_date_without_delivered_status
     OR b.dq_delivered_without_approval OR b.dq_carrier_before_purchase
     OR b.dq_delivered_before_carrier)        AS has_date_issue
FROM base AS b
LEFT JOIN items AS i USING (order_id)
LEFT JOIN payments AS p USING (order_id)
LEFT JOIN silver.order_reviews AS r USING (order_id);
