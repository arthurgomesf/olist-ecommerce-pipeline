-- gold.dim_seller
-- Grão: 1 linha por vendedor (seller_id), com a localização já conferida pelo CEP na silver.

CREATE OR REPLACE TABLE gold.dim_seller AS
SELECT
    s.seller_id,
    s.seller_zip_code_prefix,
    s.seller_city,
    s.seller_state,
    uf_region(s.seller_state)  AS seller_region,
    g.geolocation_lat          AS seller_lat,  -- coordenadas aproximadas do CEP
    g.geolocation_lng          AS seller_lng
FROM silver.sellers AS s
LEFT JOIN silver.geolocation AS g
    ON g.geolocation_zip_code_prefix = s.seller_zip_code_prefix;
