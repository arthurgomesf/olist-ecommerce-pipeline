-- gold.dim_date
-- Grão: 1 linha por dia. Calendário que cobre todos os anos com datas nos pedidos.

CREATE OR REPLACE TABLE gold.dim_date AS
WITH bounds AS (
    SELECT
        date_trunc('year', min(order_purchase_timestamp))::DATE AS first_day,
        (date_trunc('year', greatest(max(order_delivered_customer_date),
                                     max(order_estimated_delivery_date)::TIMESTAMP))
            + INTERVAL 1 YEAR - INTERVAL 1 DAY)::DATE           AS last_day
    FROM silver.orders
),

days AS (
    SELECT unnest(generate_series(first_day, last_day, INTERVAL 1 DAY))::DATE AS date_day
    FROM bounds
)

SELECT
    date_day,
    year(date_day)                 AS year,
    quarter(date_day)              AS quarter,
    month(date_day)                AS month,
    ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
     'jul', 'ago', 'set', 'out', 'nov', 'dez'][month(date_day)] AS month_name,
    strftime(date_day, '%Y-%m')    AS year_month,
    isodow(date_day)               AS day_of_week,  -- 1 = segunda ... 7 = domingo
    ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'][isodow(date_day)] AS day_name,
    isodow(date_day) IN (6, 7)     AS is_weekend
FROM days;
