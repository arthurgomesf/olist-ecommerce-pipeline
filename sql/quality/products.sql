-- Regras de qualidade de silver.products.
-- Cada SELECT é uma regra: o que foi feito, por quê, e quantas linhas foram afetadas.

SELECT
    'PRD-01' AS rule_id,
    'products' AS table_name,
    'Versões antigas do mesmo produto descartadas' AS rule,
    'remover' AS action,
    'A bronze guarda todas as versões recebidas; vale a mais recente' AS reason,
    (SELECT count(*) FROM bronze.products)
        - (SELECT count(*) FROM silver.products) AS rows_affected

UNION ALL
SELECT
    'PRD-02', 'products',
    'Medidas em formato inválido convertidas para nulo',
    'corrigir',
    'Valores chegam como texto; o que não for número inteiro válido vira nulo',
    (SELECT count(*) FROM bronze.products
     WHERE (product_name_lenght IS NOT NULL
            AND try_cast(product_name_lenght AS INTEGER) IS NULL)
        OR (product_description_lenght IS NOT NULL
            AND try_cast(product_description_lenght AS INTEGER) IS NULL)
        OR (product_photos_qty IS NOT NULL
            AND try_cast(product_photos_qty AS INTEGER) IS NULL)
        OR (product_weight_g IS NOT NULL
            AND try_cast(product_weight_g AS INTEGER) IS NULL)
        OR (product_length_cm IS NOT NULL
            AND try_cast(product_length_cm AS INTEGER) IS NULL)
        OR (product_height_cm IS NOT NULL
            AND try_cast(product_height_cm AS INTEGER) IS NULL)
        OR (product_width_cm IS NOT NULL
            AND try_cast(product_width_cm AS INTEGER) IS NULL))

UNION ALL
SELECT
    'PRD-03', 'products',
    'Produto sem categoria recebe o rótulo sem_categoria / unknown',
    'corrigir',
    'Cadastro incompleto (sem nome e fotos também); o rótulo evita perder a receita na análise',
    (SELECT count(*) FROM silver.products WHERE dq_category_missing)

UNION ALL
SELECT
    'PRD-04', 'products',
    'Categoria ausente do arquivo oficial de tradução traduzida manualmente',
    'corrigir',
    'pc_gamer e portateis_cozinha_e_preparadores_de_alimentos não têm tradução oficial',
    (SELECT count(*) FROM silver.products WHERE dq_translation_manual)

UNION ALL
SELECT
    'PRD-05', 'products',
    'Categoria sem nenhuma tradução (mantida em português)',
    'sinalizar',
    'Categoria nova sem tradução: precisa ser incluída na tradução manual',
    (SELECT count(*) FROM silver.products WHERE dq_translation_missing)

UNION ALL
SELECT
    'PRD-06', 'products',
    'Peso zero convertido para nulo',
    'corrigir',
    'Nenhum produto pesa 0 g; é erro de cadastro, então o peso fica desconhecido',
    (SELECT count(*) FROM silver.products WHERE dq_weight_fixed)
