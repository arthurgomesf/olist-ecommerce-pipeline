-- silver.geolocation
-- Grão: 1 linha por prefixo de CEP (5 dígitos).
-- A fonte tem ~1 milhão de linhas: vários pontos (lat/lng) por CEP, muitas duplicatas exatas
-- e alguns pontos fora do Brasil. Não existe chave por linha: cada linha é um ponto, então
-- a silver consolida TODOS os pontos válidos já recebidos.
-- O que esta etapa faz:
--   1. Remove duplicatas exatas (o mesmo ponto repetido).
--   2. Descarta pontos fora do território brasileiro (erros de geocodificação que caem no
--      México, em Portugal etc.). O limite leste é -32 para incluir Fernando de Noronha.
--   3. Padroniza a cidade com normalize_city() (a mesma regra de clientes e vendedores).
--   4. Consolida 1 linha por CEP: coordenadas pela mediana (resistente a pontos estranhos) e
--      a cidade/UF mais frequente no CEP (empate: ordem alfabética, para ser determinístico).

CREATE OR REPLACE TABLE silver.geolocation AS
WITH valid_points AS (
    SELECT DISTINCT
        geolocation_zip_code_prefix,
        try_cast(geolocation_lat AS DOUBLE) AS geolocation_lat,
        try_cast(geolocation_lng AS DOUBLE) AS geolocation_lng,
        normalize_city(geolocation_city)    AS geolocation_city,
        upper(trim(geolocation_state))      AS geolocation_state
    FROM bronze.geolocation
    -- Território brasileiro (com folga): latitude -34 a 5,5; longitude -74 a -32.
    WHERE try_cast(geolocation_lat AS DOUBLE) BETWEEN -34 AND 5.5
      AND try_cast(geolocation_lng AS DOUBLE) BETWEEN -74 AND -32
),

most_common_place AS (
    SELECT
        geolocation_zip_code_prefix,
        geolocation_city,
        geolocation_state
    FROM valid_points
    GROUP BY geolocation_zip_code_prefix, geolocation_city, geolocation_state
    QUALIFY row_number() OVER (
        PARTITION BY geolocation_zip_code_prefix
        ORDER BY count(*) DESC, geolocation_city, geolocation_state
    ) = 1
)

SELECT
    p.geolocation_zip_code_prefix,
    median(p.geolocation_lat) AS geolocation_lat,
    median(p.geolocation_lng) AS geolocation_lng,
    any_value(m.geolocation_city)  AS geolocation_city,
    any_value(m.geolocation_state) AS geolocation_state,
    count(*) AS points
FROM valid_points AS p
JOIN most_common_place AS m USING (geolocation_zip_code_prefix)
GROUP BY p.geolocation_zip_code_prefix;
