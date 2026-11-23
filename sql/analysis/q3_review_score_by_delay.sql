-- Q3 (Satisfação): pedidos atrasados têm nota média menor que os entregues no prazo?
-- Pedidos entregues e avaliados (uma avaliação por pedido), por faixa de atraso. As faixas
-- mostram se a nota cai conforme o atraso aumenta; "no prazo" inclui entregas antecipadas.

WITH classified AS (
    SELECT
        review_score,
        CASE
            WHEN delay_days <= 0  THEN 0
            WHEN delay_days <= 3  THEN 1
            WHEN delay_days <= 7  THEN 2
            WHEN delay_days <= 14 THEN 3
            ELSE 4
        END AS delay_bucket
    FROM gold.fct_orders
    WHERE is_delivered
      AND review_score IS NOT NULL
)

SELECT
    delay_bucket,
    ['No prazo', '1 a 3 dias', '4 a 7 dias', '8 a 14 dias', '15 dias ou mais'][delay_bucket + 1]
        AS delay_label,
    delay_bucket > 0                    AS is_late,
    count(*)                            AS orders,
    avg(review_score)                   AS avg_score,
    avg((review_score = 1)::INTEGER)    AS share_score_1,
    avg((review_score = 5)::INTEGER)    AS share_score_5
FROM classified
GROUP BY delay_bucket
ORDER BY delay_bucket;
