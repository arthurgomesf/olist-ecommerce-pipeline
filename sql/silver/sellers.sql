-- silver.sellers
-- Grão: 1 linha por vendedor (seller_id), na versão mais recente.
-- Cidade e UF do vendedor são digitadas livremente; o CEP é validado. Por isso, quando os
-- dois divergem, "o CEP manda". Depende de silver.geolocation.
-- O que esta etapa faz:
--   1. Deduplica: fica a versão mais recente de cada vendedor.
--   2. Padroniza o texto da cidade: normalize_city(); corta o que vem depois de / \ , (
--      (ex.: "maua/sao paulo" -> "maua"); remove a UF do próprio vendedor no fim
--      (ex.: "lages - sc" -> "lages", sem estragar nomes com hífen como "mogi-guacu");
--      números ou "@" no lugar da cidade (um CEP, um e-mail) viram nulo.
--   3. UF: quando a UF digitada diverge da UF do CEP, vale a do CEP (o cadastro parece vir
--      com "SP" preenchido por padrão).
--   4. Cidade: quando a cidade digitada não existe entre as cidades dos CEPs da UF (erro de
--      digitação, abreviação como "sbc", bairro, nome do estado), vale a cidade do CEP.
--   Toda correção fica marcada com uma flag dq_*.

CREATE OR REPLACE TABLE silver.sellers AS
WITH latest_version AS (
    SELECT *
    FROM bronze.sellers
    QUALIFY row_number() OVER (
        PARTITION BY seller_id
        ORDER BY _batch_id DESC, _source_file DESC, _row_hash
    ) = 1
),

typed_text AS (
    SELECT
        seller_id,
        seller_zip_code_prefix,
        seller_city               AS original_city,
        upper(trim(seller_state)) AS original_state,
        CASE
            WHEN regexp_matches(normalize_city(seller_city), '[0-9@]') THEN NULL
            ELSE trim(regexp_replace(
                regexp_replace(normalize_city(seller_city), '\s*[/\\,(].*$', ''),  -- / \ , (
                '\s*-\s*' || lower(trim(seller_state)) || '$', ''                  -- "-uf" no fim
            ))
        END AS typed_city,
        _batch_id,
        _source_file
    FROM latest_version
),

-- Todas as combinações cidade + UF que existem na base de CEPs.
known_places AS (
    SELECT DISTINCT geolocation_city AS city, geolocation_state AS state
    FROM silver.geolocation
),

located AS (
    SELECT
        t.*,
        zip.geolocation_city  AS zip_city,
        zip.geolocation_state AS zip_state,
        coalesce(zip.geolocation_state, t.original_state) AS final_state
    FROM typed_text AS t
    LEFT JOIN silver.geolocation AS zip
        ON zip.geolocation_zip_code_prefix = t.seller_zip_code_prefix
),

resolved AS (
    SELECT
        l.*,
        -- A cidade do CEP só entra se o CEP existe na base e a cidade digitada não é válida.
        (l.zip_city IS NOT NULL AND k.city IS NULL) AS use_zip_city
    FROM located AS l
    LEFT JOIN known_places AS k
        ON k.city = l.typed_city AND k.state = l.final_state
)

SELECT
    seller_id,
    seller_zip_code_prefix,
    CASE WHEN use_zip_city THEN zip_city ELSE typed_city END AS seller_city,
    final_state AS seller_state,
    _batch_id,
    _source_file,
    coalesce(typed_city <> original_city, false)    AS dq_city_fixed,
    coalesce(zip_state <> original_state, false)    AS dq_state_from_zip,
    use_zip_city                                     AS dq_city_from_zip
FROM resolved;
