-- Indicadores do topo do dashboard (uma linha), com as mesmas premissas das análises:
-- receita e pedidos = vendas concluídas (pedidos entregues); prazo e atraso = pedidos
-- entregues com data de entrega; nota = pedidos avaliados.

WITH sales AS (
    SELECT sum(price) AS revenue, count(DISTINCT order_id) AS orders
    FROM gold.fct_order_items
    WHERE is_completed_sale
),

delivery AS (
    SELECT avg(delivery_days) AS avg_delivery_days, avg(is_late::INTEGER) AS late_share
    FROM gold.fct_orders
    WHERE is_delivered
),

reviews AS (
    SELECT avg(review_score) AS avg_score
    FROM gold.fct_orders
    WHERE review_score IS NOT NULL
)

SELECT * FROM sales, delivery, reviews;
