-- silver.order_reviews
-- Grão: 1 linha por pedido (order_id): a avaliação que representa o pedido.
-- O que esta etapa faz:
--   1. Deduplica versões: fica a versão mais recente de cada avaliação (review_id + order_id).
--   2. Uma avaliação por pedido: alguns pedidos têm mais de uma (às vezes com notas
--      diferentes); vale a respondida por último, que é a opinião mais atual do cliente.
--   3. Tipa: nota em INTEGER e datas em TIMESTAMP.
--   4. Comentários só com espaços/quebras de linha viram nulo (sem comentário).

CREATE OR REPLACE TABLE silver.order_reviews AS
WITH latest_version AS (
    SELECT *
    FROM bronze.order_reviews
    QUALIFY row_number() OVER (
        PARTITION BY review_id, order_id
        ORDER BY _batch_id DESC, _source_file DESC
    ) = 1
),

typed AS (
    SELECT
        review_id,
        order_id,
        try_cast(review_score AS INTEGER) AS review_score,
        -- Remove espaços e quebras de linha das pontas; o que sobrar vazio vira nulo.
        nullif(regexp_replace(review_comment_title, '^\s+|\s+$', '', 'g'), '')
            AS review_comment_title,
        nullif(regexp_replace(review_comment_message, '^\s+|\s+$', '', 'g'), '')
            AS review_comment_message,
        try_cast(review_creation_date AS TIMESTAMP)    AS review_creation_date,
        try_cast(review_answer_timestamp AS TIMESTAMP) AS review_answer_timestamp,
        _batch_id,
        _source_file
    FROM latest_version
)

SELECT *
FROM typed
-- Uma avaliação por pedido: a respondida por último (desempates: criada por último, id).
QUALIFY row_number() OVER (
    PARTITION BY order_id
    ORDER BY review_answer_timestamp DESC NULLS LAST,
             review_creation_date DESC NULLS LAST,
             review_id
) = 1;
