-- silver.order_payments
-- Grão: 1 linha por pagamento (order_id + payment_sequential), na versão mais recente.
-- Um pedido pode ter vários pagamentos (ex.: cartão + voucher).
-- O que esta etapa faz:
--   1. Deduplica: a bronze guarda todas as versões; fica a mais recente.
--   2. Tipa: valor em DECIMAL(12,2); sequência e parcelas em INTEGER.
--   3. Remove pagamentos 'not_defined' de valor zero: não são pagamentos de fato.
--      Nada se perde: as linhas originais continuam na bronze.
--   4. Corrige parcelas = 0 para 1 (todo pagamento tem ao menos uma parcela) e marca
--      a correção com a flag dq_installments_fixed.

CREATE OR REPLACE TABLE silver.order_payments AS
WITH latest_version AS (
    SELECT *
    FROM bronze.order_payments
    QUALIFY row_number() OVER (
        PARTITION BY order_id, payment_sequential
        ORDER BY _batch_id DESC, _source_file DESC, _row_hash
    ) = 1
),

typed AS (
    SELECT
        order_id,
        try_cast(payment_sequential AS INTEGER)    AS payment_sequential,
        payment_type,
        try_cast(payment_installments AS INTEGER)  AS payment_installments,
        try_cast(payment_value AS DECIMAL(12, 2))  AS payment_value,
        _batch_id,
        _source_file
    FROM latest_version
)

SELECT
    order_id,
    payment_sequential,
    payment_type,
    CASE WHEN payment_installments = 0 THEN 1 ELSE payment_installments END
        AS payment_installments,
    payment_value,
    _batch_id,
    _source_file,
    coalesce(payment_installments = 0, false) AS dq_installments_fixed
FROM typed
-- coalesce: se o tipo vier nulo, a linha fica (só sai o 'not_defined' de valor zero).
WHERE NOT coalesce(payment_type = 'not_defined' AND payment_value = 0, false);
