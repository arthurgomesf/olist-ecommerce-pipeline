-- silver.products
-- Grão: 1 linha por produto (product_id), na versão mais recente.
-- O que esta etapa faz:
--   1. Deduplica: fica a versão mais recente de cada produto e de cada tradução.
--   2. Tipa as medidas em INTEGER e corrige o nome de duas colunas da fonte
--      (product_name_lenght / product_description_lenght -> ..._length).
--   3. Traduz a categoria para inglês com o arquivo oficial de tradução. Duas categorias
--      não estão nesse arquivo e recebem tradução manual (seguindo o padrão do oficial).
--   4. Produto sem categoria (cadastro incompleto) recebe o rótulo 'sem_categoria' /
--      'unknown' em vez de nulo, para não perder a receita dele nas análises por categoria.
--   5. Peso zero é impossível: vira nulo.
--   Toda correção fica marcada com uma flag dq_*.

CREATE OR REPLACE TABLE silver.products AS
WITH latest_version AS (
    SELECT *
    FROM bronze.products
    QUALIFY row_number() OVER (
        PARTITION BY product_id
        ORDER BY _batch_id DESC, _source_file DESC
    ) = 1
),

official_translation AS (
    SELECT product_category_name, product_category_name_english
    FROM bronze.category_translation
    QUALIFY row_number() OVER (
        PARTITION BY product_category_name
        ORDER BY _batch_id DESC, _source_file DESC
    ) = 1
),

-- Categorias presentes nos produtos, mas ausentes do arquivo oficial de tradução.
-- Se um dia entrarem no arquivo oficial, a tradução oficial passa a valer.
manual_translation AS (
    SELECT *
    FROM (VALUES
        ('pc_gamer', 'gaming_pc'),
        ('portateis_cozinha_e_preparadores_de_alimentos',
         'small_appliances_kitchen_and_food_preparers')
    ) AS t (product_category_name, product_category_name_english)
),

typed AS (
    SELECT
        p.product_id,
        p.product_category_name                            AS original_category,
        official.product_category_name_english             AS official_en,
        manual.product_category_name_english               AS manual_en,
        try_cast(p.product_name_lenght AS INTEGER)         AS product_name_length,
        try_cast(p.product_description_lenght AS INTEGER)  AS product_description_length,
        try_cast(p.product_photos_qty AS INTEGER)          AS product_photos_qty,
        try_cast(p.product_weight_g AS INTEGER)            AS product_weight_g,
        try_cast(p.product_length_cm AS INTEGER)           AS product_length_cm,
        try_cast(p.product_height_cm AS INTEGER)           AS product_height_cm,
        try_cast(p.product_width_cm AS INTEGER)            AS product_width_cm,
        p._batch_id,
        p._source_file
    FROM latest_version AS p
    LEFT JOIN official_translation AS official
        ON official.product_category_name = p.product_category_name
    LEFT JOIN manual_translation AS manual
        ON manual.product_category_name = p.product_category_name
)

SELECT
    product_id,
    coalesce(original_category, 'sem_categoria') AS product_category_name,
    CASE
        WHEN original_category IS NULL THEN 'unknown'
        -- oficial > manual > (sem tradução) mantém o nome em português
        ELSE coalesce(official_en, manual_en, original_category)
    END AS product_category_name_en,
    product_name_length,
    product_description_length,
    product_photos_qty,
    nullif(product_weight_g, 0) AS product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    _batch_id,
    _source_file,
    original_category IS NULL AS dq_category_missing,
    (official_en IS NULL AND manual_en IS NOT NULL) AS dq_translation_manual,
    (original_category IS NOT NULL AND official_en IS NULL AND manual_en IS NULL)
        AS dq_translation_missing,
    coalesce(product_weight_g = 0, false) AS dq_weight_fixed
FROM typed;
