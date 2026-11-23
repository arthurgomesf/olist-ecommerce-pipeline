-- Q1 (Vendas): como a receita total varia mês a mês?
-- Receita = soma do preço dos itens de pedidos entregues (premissa da gold), pelo mês da compra.
-- Período: jan/2017 a ago/2018, os meses com operação completa. As pontas do dataset
-- (set-dez/2016 e set-out/2018) têm poucos pedidos e distorceriam a tendência.

SELECT
    d.year_month,
    d.year,
    d.month,
    sum(i.price)                                   AS revenue,
    count(DISTINCT i.order_id)                     AS orders,
    sum(i.price) / count(DISTINCT i.order_id)      AS avg_ticket
FROM gold.fct_order_items AS i
JOIN gold.dim_date AS d ON d.date_day = i.order_purchase_date
WHERE i.is_completed_sale
  AND d.year_month BETWEEN '2017-01' AND '2018-08'
GROUP BY d.year_month, d.year, d.month
ORDER BY d.year_month;
