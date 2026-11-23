-- Regras de qualidade de silver.sellers.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.

SELECT
    'SEL-01' AS rule_id,
    'sellers' AS table_name,
    'Versões antigas do mesmo vendedor descartadas' AS rule,
    'remover' AS action,
    'A bronze guarda todas as versões recebidas; vale a mais recente' AS reason,
    (SELECT count(*) FROM bronze.sellers)
        - (SELECT count(*) FROM silver.sellers) AS rows_affected

UNION ALL
SELECT
    'SEL-02', 'sellers',
    'Cidade padronizada (acento, espaços, UF e textos extras removidos)',
    'corrigir',
    'A cidade é digitada livremente (ex.: "sao paulo / sao paulo", "lages - sc")',
    (SELECT count(*) FROM silver.sellers WHERE dq_city_fixed)

UNION ALL
SELECT
    'SEL-03', 'sellers',
    'Cidade inválida (números ou e-mail no lugar do nome) convertida para nulo',
    'corrigir',
    'Não é nome de cidade; a UF e o CEP do vendedor continuam válidos',
    (SELECT count(*) FROM silver.sellers WHERE dq_city_invalid)
