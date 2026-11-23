-- Checagens de integridade da gold (o "portão de qualidade" do pipeline).
-- Cada SELECT conta violações: o esperado é SEMPRE 0. Se alguma checagem falhar, o pipeline
-- para com erro antes de gerar a documentação.

-- 1. Chaves únicas e preenchidas -----------------------------------------------------------
SELECT
    'CHK-01' AS check_id,
    'dim_date: date_day único e preenchido' AS description,
    (SELECT count(*) - count(DISTINCT date_day) FROM gold.dim_date) AS failures
UNION ALL
SELECT 'CHK-02', 'dim_customer: customer_id único e preenchido',
    (SELECT count(*) - count(DISTINCT customer_id) FROM gold.dim_customer)
UNION ALL
SELECT 'CHK-03', 'dim_seller: seller_id único e preenchido',
    (SELECT count(*) - count(DISTINCT seller_id) FROM gold.dim_seller)
UNION ALL
SELECT 'CHK-04', 'dim_product: product_id único e preenchido',
    (SELECT count(*) - count(DISTINCT product_id) FROM gold.dim_product)
UNION ALL
SELECT 'CHK-05', 'fct_orders: order_id único e preenchido',
    (SELECT count(*) - count(DISTINCT order_id) FROM gold.fct_orders)
UNION ALL
SELECT 'CHK-06', 'fct_order_items: (order_id, order_item_id) único e preenchido',
    (SELECT count(*) FROM gold.fct_order_items)
    - (SELECT count(*) FROM (SELECT DISTINCT order_id, order_item_id FROM gold.fct_order_items))
    + (SELECT count(*) FROM gold.fct_order_items
       WHERE order_id IS NULL OR order_item_id IS NULL)
UNION ALL
SELECT 'CHK-07', 'fct_payments: (order_id, payment_sequential) único e preenchido',
    (SELECT count(*) FROM gold.fct_payments)
    - (SELECT count(*) FROM (SELECT DISTINCT order_id, payment_sequential FROM gold.fct_payments))
    + (SELECT count(*) FROM gold.fct_payments
       WHERE order_id IS NULL OR payment_sequential IS NULL)

-- 2. Integridade referencial: todo fato aponta para algo que existe ----------------------
UNION ALL
SELECT 'CHK-08', 'fct_orders: todo customer_id existe em dim_customer',
    (SELECT count(*) FROM gold.fct_orders AS f
     WHERE NOT EXISTS (SELECT 1 FROM gold.dim_customer AS d WHERE d.customer_id = f.customer_id))
UNION ALL
SELECT 'CHK-09', 'fct_orders: toda data de compra existe em dim_date',
    (SELECT count(*) FROM gold.fct_orders AS f
     WHERE NOT EXISTS (SELECT 1 FROM gold.dim_date AS d WHERE d.date_day = f.order_purchase_date))
UNION ALL
SELECT 'CHK-10', 'fct_order_items: todo item pertence a um pedido de fct_orders',
    (SELECT count(*) FROM gold.fct_order_items AS f
     WHERE NOT EXISTS (SELECT 1 FROM gold.fct_orders AS o WHERE o.order_id = f.order_id))
UNION ALL
SELECT 'CHK-11', 'fct_order_items: todo product_id existe em dim_product',
    (SELECT count(*) FROM gold.fct_order_items AS f
     WHERE NOT EXISTS (SELECT 1 FROM gold.dim_product AS d WHERE d.product_id = f.product_id))
UNION ALL
SELECT 'CHK-12', 'fct_order_items: todo seller_id existe em dim_seller',
    (SELECT count(*) FROM gold.fct_order_items AS f
     WHERE NOT EXISTS (SELECT 1 FROM gold.dim_seller AS d WHERE d.seller_id = f.seller_id))
UNION ALL
SELECT 'CHK-13', 'fct_payments: todo pagamento pertence a um pedido de fct_orders',
    (SELECT count(*) FROM gold.fct_payments AS f
     WHERE NOT EXISTS (SELECT 1 FROM gold.fct_orders AS o WHERE o.order_id = f.order_id))

-- 3. Valores dentro do domínio esperado ----------------------------------------------------
UNION ALL
SELECT 'CHK-14', 'fct_orders: nota da avaliação entre 1 e 5',
    (SELECT count(*) FROM gold.fct_orders WHERE review_score NOT BETWEEN 1 AND 5)
UNION ALL
SELECT 'CHK-15', 'fct_orders: prazo de entrega nunca negativo',
    (SELECT count(*) FROM gold.fct_orders WHERE delivery_days < 0)
UNION ALL
SELECT 'CHK-16', 'fct_order_items: preço maior que zero',
    (SELECT count(*) FROM gold.fct_order_items WHERE NOT coalesce(price > 0, false))
UNION ALL
SELECT 'CHK-17', 'fct_payments: valor pago nunca negativo',
    (SELECT count(*) FROM gold.fct_payments WHERE payment_value < 0)

-- 4. Reconciliação: nada se perde nem se duplica entre as camadas -------------------------
UNION ALL
SELECT 'CHK-18', 'fct_orders tem exatamente os pedidos da silver',
    abs((SELECT count(*) FROM gold.fct_orders) - (SELECT count(*) FROM silver.orders))
UNION ALL
SELECT 'CHK-19', 'Soma dos preços: fct_order_items = silver.order_items',
    CASE WHEN (SELECT sum(price) FROM gold.fct_order_items)
              IS DISTINCT FROM (SELECT sum(price) FROM silver.order_items) THEN 1 ELSE 0 END
UNION ALL
SELECT 'CHK-20', 'Soma dos itens por pedido: fct_orders = fct_order_items',
    CASE WHEN (SELECT sum(items_value) FROM gold.fct_orders)
              IS DISTINCT FROM (SELECT sum(price) FROM gold.fct_order_items) THEN 1 ELSE 0 END
UNION ALL
SELECT 'CHK-21', 'Soma dos pagamentos: fct_orders = fct_payments',
    CASE WHEN (SELECT sum(payment_value) FROM gold.fct_orders)
              IS DISTINCT FROM (SELECT sum(payment_value) FROM gold.fct_payments) THEN 1 ELSE 0 END
