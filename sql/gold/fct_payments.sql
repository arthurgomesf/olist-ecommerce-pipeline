-- gold.fct_payments
-- Grão: 1 linha por pagamento (order_id + payment_sequential). Um pedido pode ser pago com
-- mais de um meio (ex.: cartão + voucher), por isso os pagamentos têm o próprio fato.

CREATE OR REPLACE TABLE gold.fct_payments AS
SELECT
    p.order_id,
    p.payment_sequential,
    p.payment_type,
    p.payment_installments,
    p.payment_value,
    o.order_purchase_timestamp::DATE  AS order_purchase_date,  -- liga com dim_date
    o.order_status,
    is_completed_sale(o.order_status) AS is_completed_sale
FROM silver.order_payments AS p
LEFT JOIN silver.orders AS o USING (order_id);
