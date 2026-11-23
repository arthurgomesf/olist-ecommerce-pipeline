-- Regras de qualidade de silver.order_payments.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.

SELECT
    'PAY-01' AS rule_id,
    'order_payments' AS table_name,
    'Versões antigas do mesmo pagamento descartadas' AS rule,
    'remover' AS action,
    'A bronze guarda todas as versões recebidas; vale a mais recente' AS reason,
    (SELECT count(*) FROM bronze.order_payments)
        - (SELECT count(*) FROM (SELECT DISTINCT order_id, payment_sequential
                                 FROM bronze.order_payments)) AS rows_affected

UNION ALL
SELECT
    'PAY-02', 'order_payments',
    'Números em formato inválido convertidos para nulo',
    'corrigir',
    'Valores chegam como texto; o que não for número válido vira nulo',
    (SELECT count(*) FROM bronze.order_payments
     WHERE (payment_sequential IS NOT NULL
            AND try_cast(payment_sequential AS INTEGER) IS NULL)
        OR (payment_installments IS NOT NULL
            AND try_cast(payment_installments AS INTEGER) IS NULL)
        OR (payment_value IS NOT NULL
            AND try_cast(payment_value AS DECIMAL(12, 2)) IS NULL))

UNION ALL
SELECT
    'PAY-03', 'order_payments',
    'Pagamentos do tipo not_defined com valor zero removidos',
    'remover',
    'Sem tipo e sem valor não é pagamento de fato; as linhas seguem guardadas na bronze',
    (SELECT count(*) FROM (SELECT DISTINCT order_id, payment_sequential
                           FROM bronze.order_payments))
        - (SELECT count(*) FROM silver.order_payments)

UNION ALL
SELECT
    'PAY-04', 'order_payments',
    'Pagamentos com 0 parcelas corrigidos para 1',
    'corrigir',
    'Todo pagamento tem ao menos uma parcela; marcado em dq_installments_fixed',
    (SELECT count(*) FROM silver.order_payments WHERE dq_installments_fixed)

UNION ALL
SELECT
    'PAY-05', 'order_payments',
    'Pedidos sem nenhum pagamento',
    'manter',
    'Pedido segue válido; o total pago fica vazio. Receita é calculada pelos itens',
    (SELECT count(*) FROM silver.orders AS o
     WHERE NOT EXISTS (SELECT 1 FROM silver.order_payments AS p
                       WHERE p.order_id = o.order_id))

UNION ALL
SELECT
    'PAY-06', 'order_payments',
    'Pedidos cujo total pago difere de itens + frete em mais de R$ 0,01',
    'manter',
    'Juros de parcelamento e vouchers explicam a diferença; por isso a receita vem dos itens',
    (SELECT count(*)
     FROM (SELECT order_id, sum(price + freight_value) AS items_total
           FROM silver.order_items GROUP BY order_id) AS i
     JOIN (SELECT order_id, sum(payment_value) AS paid_total
           FROM silver.order_payments GROUP BY order_id) AS p USING (order_id)
     WHERE abs(p.paid_total - i.items_total) > 0.01)
