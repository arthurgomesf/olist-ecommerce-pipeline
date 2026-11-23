-- Regras de qualidade de silver.order_items.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.

SELECT
    'ITM-01' AS rule_id,
    'order_items' AS table_name,
    'Versões antigas do mesmo item descartadas' AS rule,
    'remover' AS action,
    'A bronze guarda todas as versões recebidas; vale a mais recente' AS reason,
    (SELECT count(*) FROM bronze.order_items)
        - (SELECT count(*) FROM silver.order_items) AS rows_affected

UNION ALL
SELECT
    'ITM-02', 'order_items',
    'Números e datas em formato inválido convertidos para nulo',
    'corrigir',
    'Valores chegam como texto; o que não for número ou data válida vira nulo',
    (SELECT count(*) FROM bronze.order_items
     WHERE (order_item_id IS NOT NULL AND try_cast(order_item_id AS INTEGER) IS NULL)
        OR (shipping_limit_date IS NOT NULL
            AND try_cast(shipping_limit_date AS TIMESTAMP) IS NULL)
        OR (price IS NOT NULL AND try_cast(price AS DECIMAL(12, 2)) IS NULL)
        OR (freight_value IS NOT NULL
            AND try_cast(freight_value AS DECIMAL(12, 2)) IS NULL))

UNION ALL
SELECT
    'ITM-03', 'order_items',
    'Preço fora da faixa esperada (zero/negativo ou acima de R$ 10.000)',
    'sinalizar',
    'O maior preço do histórico é R$ 6.735; valor fora da faixa precisa de verificação',
    (SELECT count(*) FROM silver.order_items WHERE dq_price_out_of_range)

UNION ALL
SELECT
    'ITM-04', 'order_items',
    'Data-limite de envio mais de 1 ano após a compra',
    'sinalizar',
    'Datas em 2020 para compras de 2017 (mediana: 6 dias); coluna não usada nas análises',
    (SELECT count(*) FROM silver.order_items WHERE dq_shipping_limit_too_far)

UNION ALL
SELECT
    'ITM-05', 'order_items',
    'Itens com frete zero',
    'manter',
    'Frete grátis é plausível (promoção); mantido e registrado para transparência',
    (SELECT count(*) FROM silver.order_items WHERE freight_value = 0)
