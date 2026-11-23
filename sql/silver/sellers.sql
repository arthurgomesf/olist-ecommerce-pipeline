-- silver.sellers
-- Grão: 1 linha por vendedor (seller_id), na versão mais recente.
-- O que esta etapa faz:
--   1. Deduplica: fica a versão mais recente de cada vendedor.
--   2. Padroniza a cidade, que é digitada livremente pelo vendedor:
--        - minúsculas, sem acento, sem espaços repetidos; "´" vira apóstrofo;
--        - corta o que vem depois de / \ , ( (ex.: "maua/sao paulo" -> "maua");
--        - remove a UF do próprio vendedor no fim (ex.: "lages - sc" -> "lages"). Só a UF
--          do vendedor é removida, para não estragar nomes com hífen como "mogi-guacu".
--      Correções ficam marcadas em dq_city_fixed.
--   3. Cidade com números ou "@" (ex.: um CEP ou um e-mail no lugar da cidade) vira nulo
--      e fica marcada em dq_city_invalid.

CREATE OR REPLACE TABLE silver.sellers AS
WITH latest_version AS (
    SELECT *
    FROM bronze.sellers
    QUALIFY row_number() OVER (
        PARTITION BY seller_id
        ORDER BY _batch_id DESC, _source_file DESC
    ) = 1
),

base AS (
    SELECT
        seller_id,
        seller_zip_code_prefix,
        seller_city AS original_city,
        upper(trim(seller_state)) AS seller_state,
        regexp_replace(lower(strip_accents(trim(replace(seller_city, '´', '''')))), '\s+', ' ', 'g')
            AS city_lower,
        _batch_id,
        _source_file
    FROM latest_version
),

standardized AS (
    SELECT
        *,
        CASE
            WHEN regexp_matches(city_lower, '[0-9@]') THEN NULL
            ELSE trim(regexp_replace(
                regexp_replace(city_lower, '\s*[/\\,(].*$', ''),           -- corta em / \ , (
                '\s*-\s*' || lower(seller_state) || '$', ''                -- remove "-uf" no fim
            ))
        END AS seller_city
    FROM base
)

SELECT
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    _batch_id,
    _source_file,
    coalesce(seller_city <> original_city, false) AS dq_city_fixed,
    (original_city IS NOT NULL AND seller_city IS NULL) AS dq_city_invalid
FROM standardized;
