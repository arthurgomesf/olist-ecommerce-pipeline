-- Regras de qualidade de silver.orders.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.
-- Ações: remover | corrigir | sinalizar (o registro fica, marcado com uma flag dq_*).

SELECT
    'ORD-01' AS rule_id,
    'orders' AS table_name,
    'Versões antigas do mesmo pedido descartadas' AS rule,
    'remover' AS action,
    'A bronze guarda todas as versões recebidas; vale a mais recente' AS reason,
    (SELECT count(*) FROM bronze.orders) - (SELECT count(*) FROM silver.orders) AS rows_affected

UNION ALL
SELECT
    'ORD-02', 'orders',
    'Datas em formato inválido convertidas para nulo',
    'corrigir',
    'Datas chegam como texto; o que não for data válida vira nulo em vez de quebrar a carga',
    (SELECT count(*) FROM bronze.orders
     WHERE (order_purchase_timestamp IS NOT NULL
            AND try_cast(order_purchase_timestamp AS TIMESTAMP) IS NULL)
        OR (order_approved_at IS NOT NULL
            AND try_cast(order_approved_at AS TIMESTAMP) IS NULL)
        OR (order_delivered_carrier_date IS NOT NULL
            AND try_cast(order_delivered_carrier_date AS TIMESTAMP) IS NULL)
        OR (order_delivered_customer_date IS NOT NULL
            AND try_cast(order_delivered_customer_date AS TIMESTAMP) IS NULL)
        OR (order_estimated_delivery_date IS NOT NULL
            AND try_cast(order_estimated_delivery_date AS DATE) IS NULL))

UNION ALL
SELECT
    'ORD-03', 'orders',
    'Pedido entregue (delivered) sem data de entrega',
    'sinalizar',
    'Sem a data não há como medir prazo; fica fora das métricas de entrega',
    (SELECT count(*) FROM silver.orders WHERE dq_delivered_without_date)

UNION ALL
SELECT
    'ORD-04', 'orders',
    'Pedido com data de entrega, mas status diferente de delivered',
    'sinalizar',
    'O status é a fonte da verdade; fica fora das métricas de entrega',
    (SELECT count(*) FROM silver.orders WHERE dq_date_without_delivered_status)

UNION ALL
SELECT
    'ORD-05', 'orders',
    'Pedido entregue sem data de aprovação do pagamento',
    'sinalizar',
    'Não afeta o prazo (compra -> entrega); mantido e marcado',
    (SELECT count(*) FROM silver.orders WHERE dq_delivered_without_approval)

UNION ALL
SELECT
    'ORD-06', 'orders',
    'Coleta pela transportadora registrada antes da compra',
    'sinalizar',
    'Erro de registro na data de coleta; não afeta o prazo compra -> entrega',
    (SELECT count(*) FROM silver.orders WHERE dq_carrier_before_purchase)

UNION ALL
SELECT
    'ORD-07', 'orders',
    'Entrega ao cliente registrada antes da coleta pela transportadora',
    'sinalizar',
    'Datas intermediárias inconsistentes; o prazo compra -> entrega continua válido',
    (SELECT count(*) FROM silver.orders WHERE dq_delivered_before_carrier)
