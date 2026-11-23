-- gold.dim_product
-- Grão: 1 linha por produto (product_id), com a categoria em português e em inglês.

CREATE OR REPLACE TABLE gold.dim_product AS
SELECT
    product_id,
    product_category_name,     -- português ('sem_categoria' quando a fonte não informa)
    product_category_name_en,  -- inglês ('unknown' quando a fonte não informa)
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
FROM silver.products;
