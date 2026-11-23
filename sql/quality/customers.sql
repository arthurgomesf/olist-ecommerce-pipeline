-- Regras de qualidade de silver.customers.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.

SELECT
    'CUS-01' AS rule_id,
    'customers' AS table_name,
    'Versões antigas do mesmo customer_id descartadas' AS rule,
    'remover' AS action,
    'A bronze guarda todas as versões recebidas; vale a mais recente' AS reason,
    (SELECT count(*) FROM bronze.customers)
        - (SELECT count(*) FROM silver.customers) AS rows_affected

UNION ALL
SELECT
    'CUS-02', 'customers',
    'Cidade padronizada (minúsculas, sem acento, sem espaços repetidos)',
    'corrigir',
    'Mesma cidade escrita de jeitos diferentes viraria cidades diferentes nas análises',
    (SELECT count(*) FROM silver.customers WHERE dq_city_fixed)

UNION ALL
SELECT
    'CUS-03', 'customers',
    'Mesmo cliente (customer_unique_id) com vários customer_id',
    'manter',
    'Esperado: o customer_id é gerado a cada pedido. Clientes e recompra usam customer_unique_id',
    (SELECT count(*) FROM (SELECT customer_unique_id FROM silver.customers
                           GROUP BY customer_unique_id HAVING count(*) > 1))

UNION ALL
SELECT
    'CUS-04', 'customers',
    'Clientes cuja UF diverge da UF do CEP (verificação)',
    'manter',
    'A UF do cliente vem do sistema, não é digitada; se bate com o CEP, as análises por estado são confiáveis',
    (SELECT count(*)
     FROM silver.customers AS c
     JOIN silver.geolocation AS g
         ON g.geolocation_zip_code_prefix = c.customer_zip_code_prefix
     WHERE g.geolocation_state <> c.customer_state)
