-- Regras de qualidade de silver.geolocation.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.
-- As contagens fecham com a silver: linhas da bronze - GEO-01 - GEO-02 = soma de "points".

WITH points AS (
    -- A mesma projeção usada na silver: um ponto por CEP, coordenada, cidade padronizada e UF.
    SELECT DISTINCT
        geolocation_zip_code_prefix,
        try_cast(geolocation_lat AS DOUBLE) AS lat,
        try_cast(geolocation_lng AS DOUBLE) AS lng,
        normalize_city(geolocation_city)    AS city,
        upper(trim(geolocation_state))      AS state
    FROM bronze.geolocation
)

SELECT
    'GEO-01' AS rule_id,
    'geolocation' AS table_name,
    'Pontos duplicados removidos (iguais depois de padronizar a cidade)' AS rule,
    'remover' AS action,
    'O mesmo ponto repetido não traz informação e distorceria a consolidação' AS reason,
    (SELECT count(*) FROM bronze.geolocation) - (SELECT count(*) FROM points) AS rows_affected

UNION ALL
SELECT
    'GEO-02', 'geolocation',
    'Pontos fora do território brasileiro (ou sem coordenada válida) descartados',
    'remover',
    'Erros de geocodificação (ex.: coordenadas no México ou em Portugal) puxariam a média do CEP',
    (SELECT count(*) FROM points
     WHERE NOT coalesce(lat BETWEEN -34 AND 5.5 AND lng BETWEEN -74 AND -32, false))

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
        SELECT seller_zip_code_prefix FROM silver.sellers) AS z
     WHERE NOT EXISTS (SELECT 1 FROM silver.geolocation AS g
                       WHERE g.geolocation_zip_code_prefix = z.zip))
