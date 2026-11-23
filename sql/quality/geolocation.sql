-- Regras de qualidade de silver.geolocation.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.

SELECT
    'GEO-01' AS rule_id,
    'geolocation' AS table_name,
    'Pontos duplicados exatos removidos' AS rule,
    'remover' AS action,
    'O mesmo ponto repetido não traz informação e distorceria a consolidação' AS reason,
    (SELECT count(*) FROM bronze.geolocation)
        - (SELECT count(*) FROM (SELECT DISTINCT geolocation_zip_code_prefix, geolocation_lat,
                                        geolocation_lng, geolocation_city, geolocation_state
                                 FROM bronze.geolocation)) AS rows_affected

UNION ALL
SELECT
    'GEO-02', 'geolocation',
    'Pontos fora do território brasileiro (ou sem coordenada válida) descartados',
    'remover',
    'Erros de geocodificação (ex.: coordenadas no México ou em Portugal) puxariam a média do CEP',
    (SELECT count(*) FROM (
        SELECT DISTINCT geolocation_zip_code_prefix, geolocation_lat, geolocation_lng,
                        geolocation_city, geolocation_state
        FROM bronze.geolocation
        WHERE NOT coalesce(try_cast(geolocation_lat AS DOUBLE) BETWEEN -34 AND 5.5
                           AND try_cast(geolocation_lng AS DOUBLE) BETWEEN -74 AND -32, false)))

UNION ALL
SELECT
    'GEO-03', 'geolocation',
    'Cidade padronizada (minúsculas, sem acento, sem espaços repetidos)',
    'corrigir',
    'A mesma cidade aparecia com e sem acento (ex.: "são paulo" e "sao paulo")',
    (SELECT count(*) FROM (
        SELECT DISTINCT geolocation_zip_code_prefix, geolocation_lat, geolocation_lng,
                        geolocation_city, geolocation_state
        FROM bronze.geolocation)
     WHERE normalize_city(geolocation_city) <> geolocation_city)

UNION ALL
SELECT
    'GEO-04', 'geolocation',
    'CEPs de clientes ou vendedores ausentes da base de geolocalização',
    'manter',
    'Ficam sem coordenadas; cidade e UF continuam vindo do próprio cadastro',
    (SELECT count(*) FROM (
        SELECT customer_zip_code_prefix AS zip FROM silver.customers
        UNION
        SELECT seller_zip_code_prefix FROM silver.sellers)
     WHERE zip NOT IN (SELECT geolocation_zip_code_prefix FROM silver.geolocation))
