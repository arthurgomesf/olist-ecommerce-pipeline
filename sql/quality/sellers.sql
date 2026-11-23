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
    'Texto da cidade padronizado (acento, espaços, UF e textos extras removidos)',
    'corrigir',
    'A cidade é digitada livremente (ex.: "sao paulo / sao paulo", "lages - sc")',
    (SELECT count(*) FROM silver.sellers WHERE dq_city_fixed)

UNION ALL
SELECT
    'SEL-03', 'sellers',
    'UF digitada diferente da UF do CEP: vale a UF do CEP',
    'corrigir',
    'O CEP é validado e a UF é digitada; o cadastro parece vir com "SP" por padrão',
    (SELECT count(*) FROM silver.sellers WHERE dq_state_from_zip)

UNION ALL
SELECT
    'SEL-04', 'sellers',
    'Cidade inexistente na base de CEPs da UF substituída pela cidade do CEP',
    'corrigir',
    'Erros de digitação, abreviações ("sbc"), bairros, nome do estado ou texto inválido',
    (SELECT count(*) FROM silver.sellers WHERE dq_city_from_zip)
