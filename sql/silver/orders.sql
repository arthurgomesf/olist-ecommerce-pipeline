-- silver.orders
-- Grão: 1 linha por pedido (order_id), na versão mais recente recebida.
-- O que esta etapa faz:
--   1. Deduplica: a bronze guarda todas as versões de um pedido; fica a mais recente.
--   2. Tipa: datas saem de texto para TIMESTAMP. A data estimada vira DATE, pois
--      sempre vem com hora 00:00:00 (é uma data, não um momento).
--   3. Sinaliza: inconsistências de datas viram flags dq_* (data quality).
--      Nenhum pedido é apagado por causa delas.

CREATE OR REPLACE TABLE silver.orders AS
WITH latest_version AS (
    SELECT *
    FROM bronze.orders
    -- Mais recente = maior lote; dentro do mesmo lote, o arquivo que vem depois na
    -- ordem alfabética (ex.: olist_orders_dataset_2018-11.csv depois do original).
    QUALIFY row_number() OVER (
        PARTITION BY order_id
        ORDER BY _batch_id DESC, _source_file DESC
    ) = 1
),

typed AS (
    SELECT
        order_id,
        customer_id,
        order_status,
        try_cast(order_purchase_timestamp AS TIMESTAMP)      AS order_purchase_timestamp,
        try_cast(order_approved_at AS TIMESTAMP)             AS order_approved_at,
        try_cast(order_delivered_carrier_date AS TIMESTAMP)  AS order_delivered_carrier_date,
        try_cast(order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_date,
        try_cast(order_estimated_delivery_date AS DATE)      AS order_estimated_delivery_date,
        _batch_id,
        _source_file
    FROM latest_version
)

SELECT
    *,
    -- Flags de qualidade: true = inconsistência encontrada.
    coalesce(order_status = 'delivered' AND order_delivered_customer_date IS NULL, false)
        AS dq_delivered_without_date,
    coalesce(order_status <> 'delivered' AND order_delivered_customer_date IS NOT NULL, false)
        AS dq_date_without_delivered_status,
    coalesce(order_status = 'delivered' AND order_approved_at IS NULL, false)
        AS dq_delivered_without_approval,
    coalesce(order_delivered_carrier_date < order_purchase_timestamp, false)
        AS dq_carrier_before_purchase,
    coalesce(order_delivered_customer_date < order_delivered_carrier_date, false)
        AS dq_delivered_before_carrier
FROM typed;
