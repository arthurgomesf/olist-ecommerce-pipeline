-- Q2 (Logística): qual o tempo médio de entrega, em dias, por estado?
-- Pedidos entregues (com data de entrega), pelo estado do endereço de entrega do cliente.
-- Além da média, traz a mediana (resistente a casos extremos), o prazo prometido médio e a
-- parcela de pedidos atrasados: demorar não é o mesmo que atrasar.

SELECT
    c.customer_state              AS state,
    c.customer_region             AS region,
    count(*)                      AS orders,
    avg(o.delivery_days)          AS avg_delivery_days,
    median(o.delivery_days)       AS median_delivery_days,
    avg(o.estimated_days)         AS avg_promised_days,
    avg(o.is_late::INTEGER)       AS late_share
FROM gold.fct_orders AS o
JOIN gold.dim_customer AS c USING (customer_id)
WHERE o.is_delivered
GROUP BY c.customer_state, c.customer_region
ORDER BY avg_delivery_days DESC;
