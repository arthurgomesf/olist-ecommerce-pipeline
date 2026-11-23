-- Q5 (Clientes): qual a porcentagem de clientes que compraram mais de uma vez?
-- Cliente = customer_unique_id (o customer_id muda a cada pedido). Compra = pedido entregue.
-- Distribuição dos clientes pelo número de compras. Também conta quem comprou em pelo menos
-- dois DIAS diferentes: dois pedidos no mesmo dia costumam ser a mesma sessão de compra.

WITH per_customer AS (
    SELECT
        c.customer_unique_id,
        count(DISTINCT o.order_id)             AS purchases,
        count(DISTINCT o.order_purchase_date)  AS purchase_days
    FROM gold.fct_orders AS o
    JOIN gold.dim_customer AS c USING (customer_id)
    WHERE o.is_completed_sale
    GROUP BY c.customer_unique_id
)

SELECT
    CASE WHEN purchases >= 4 THEN '4+' ELSE purchases::VARCHAR END  AS purchases,
    count(*)                                                        AS customers,
    count(*) FILTER (WHERE purchase_days >= 2)                      AS customers_on_2plus_days
FROM per_customer
GROUP BY 1
ORDER BY 1;
