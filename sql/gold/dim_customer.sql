-- gold.dim_customer
-- Grão: 1 linha por customer_id (o "cliente do pedido", com o endereço daquela entrega).
-- Por que esse grão: na Olist o customer_id é gerado a cada pedido e carrega o endereço de
-- entrega, que é o que importa para logística por estado. A pessoa (customer_unique_id) fica
-- como atributo, para medir recompra.

CREATE OR REPLACE TABLE gold.dim_customer AS
SELECT
    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    uf_region(c.customer_state)  AS customer_region,
    g.geolocation_lat            AS customer_lat,  -- coordenadas aproximadas do CEP
    g.geolocation_lng            AS customer_lng
FROM silver.customers AS c
LEFT JOIN silver.geolocation AS g
    ON g.geolocation_zip_code_prefix = c.customer_zip_code_prefix;
