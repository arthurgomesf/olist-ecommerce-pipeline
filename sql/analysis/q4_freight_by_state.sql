-- Q4 (Financeiro): qual o valor médio do frete por estado do cliente?
-- Frete por PEDIDO (soma do frete dos itens), em pedidos entregues: é o valor que o cliente
-- paga na compra. A média por item subestimaria os pedidos com vários itens.
-- O peso do frete compara o frete total com o valor total dos itens do estado.

SELECT
    c.customer_state                              AS state,
    c.customer_region                             AS region,
    count(*)                                      AS orders,
    avg(o.freight_value)                          AS avg_freight,
    sum(o.freight_value) / sum(o.items_value)     AS freight_share_of_items
FROM gold.fct_orders AS o
JOIN gold.dim_customer AS c USING (customer_id)
WHERE o.is_completed_sale
GROUP BY c.customer_state, c.customer_region
ORDER BY avg_freight DESC;
