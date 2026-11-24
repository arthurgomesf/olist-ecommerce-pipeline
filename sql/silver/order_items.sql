-- silver.order_items
-- Grão: 1 linha por item de pedido (order_id + order_item_id), na versão mais recente.
-- O que esta etapa faz:
--   1. Deduplica: a bronze guarda todas as versões de um item; fica a mais recente.
--   2. Tipa: preço e frete em DECIMAL(12,2) (dinheiro sem erro de arredondamento de
--      ponto flutuante) e data-limite de envio em TIMESTAMP.
--   3. Sinaliza: preço fora da faixa esperada e data-limite de envio absurda.
-- Depende de silver.orders (usa a data da compra para avaliar a data-limite de envio).

CREATE OR REPLACE TABLE silver.order_items AS
WITH latest_version AS (
    SELECT *
    FROM bronze.order_items
    QUALIFY row_number() OVER (
        PARTITION BY order_id, order_item_id
        ORDER BY _batch_id DESC, _source_file DESC, _row_hash
    ) = 1
),

typed AS (
    SELECT
        order_id,
        try_cast(order_item_id AS INTEGER)          AS order_item_id,
        product_id,
        seller_id,
        try_cast(shipping_limit_date AS TIMESTAMP)  AS shipping_limit_date,
        try_cast(price AS DECIMAL(12, 2))           AS price,
        try_cast(freight_value AS DECIMAL(12, 2))   AS freight_value,
        _batch_id,
        _source_file
    FROM latest_version
)

SELECT
    i.*,
    -- O maior preço do histórico é R$ 6.735: zero/negativo ou acima de R$ 10.000 é suspeito.
    coalesce(i.price <= 0 OR i.price > 10000, false) AS dq_price_out_of_range,
    -- No histórico, a data-limite fica em mediana 6 dias após a compra; mais de 1 ano é erro.
    coalesce(date_diff('day', o.order_purchase_timestamp, i.shipping_limit_date) > 365, false)
        AS dq_shipping_limit_too_far
FROM typed AS i
LEFT JOIN silver.orders AS o USING (order_id);
