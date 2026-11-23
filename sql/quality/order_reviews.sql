-- Regras de qualidade de silver.order_reviews.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.

SELECT
    'REV-01' AS rule_id,
    'order_reviews' AS table_name,
    'Versões antigas da mesma avaliação descartadas' AS rule,
    'remover' AS action,
    'A bronze guarda todas as versões recebidas; vale a mais recente' AS reason,
    (SELECT count(*) FROM bronze.order_reviews)
        - (SELECT count(*) FROM (SELECT DISTINCT review_id, order_id
                                 FROM bronze.order_reviews)) AS rows_affected

UNION ALL
SELECT
    'REV-02', 'order_reviews',
    'Notas e datas em formato inválido convertidas para nulo',
    'corrigir',
    'Valores chegam como texto; o que não for número ou data válida vira nulo',
    (SELECT count(*) FROM bronze.order_reviews
     WHERE (review_score IS NOT NULL AND try_cast(review_score AS INTEGER) IS NULL)
        OR (review_creation_date IS NOT NULL
            AND try_cast(review_creation_date AS TIMESTAMP) IS NULL)
        OR (review_answer_timestamp IS NOT NULL
            AND try_cast(review_answer_timestamp AS TIMESTAMP) IS NULL))

UNION ALL
SELECT
    'REV-03', 'order_reviews',
    'Avaliações extras do mesmo pedido descartadas (fica a respondida por último)',
    'remover',
    'Uma nota por pedido evita contar o pedido duas vezes; a mais recente é a opinião atual',
    (SELECT count(*) FROM (SELECT DISTINCT review_id, order_id FROM bronze.order_reviews))
        - (SELECT count(*) FROM silver.order_reviews)

UNION ALL
SELECT
    'REV-04', 'order_reviews',
    'Comentários só com espaços ou quebras de linha convertidos para nulo',
    'corrigir',
    'Texto vazio não é comentário; padroniza a ausência de comentário como nulo',
    (SELECT count(*) FROM bronze.order_reviews
     WHERE regexp_replace(review_comment_title, '^\s+|\s+$', '', 'g') = ''
        OR regexp_replace(review_comment_message, '^\s+|\s+$', '', 'g') = '')

UNION ALL
SELECT
    'REV-05', 'order_reviews',
    'Avaliações sem comentário escrito',
    'manter',
    'O comentário é opcional; a nota (campo usado nas análises) está sempre preenchida',
    (SELECT count(*) FROM silver.order_reviews WHERE review_comment_message IS NULL)

UNION ALL
SELECT
    'REV-06', 'order_reviews',
    'Pedidos sem nenhuma avaliação',
    'manter',
    'Avaliar é opcional; esses pedidos ficam fora das análises de satisfação',
    (SELECT count(*) FROM silver.orders AS o
     WHERE NOT EXISTS (SELECT 1 FROM silver.order_reviews AS r
                       WHERE r.order_id = o.order_id))
