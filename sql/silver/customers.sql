-- silver.customers
-- Grão: 1 linha por customer_id, na versão mais recente.
-- Atenção: na Olist o customer_id é gerado A CADA PEDIDO (é o "cliente do pedido", com o
-- endereço daquela entrega). A pessoa é o customer_unique_id: para contar clientes ou
-- medir recompra, use customer_unique_id.
-- O que esta etapa faz:
--   1. Deduplica: fica a versão mais recente de cada customer_id.
--   2. Padroniza: cidade com normalize_city() (minúsculas, sem acento, sem espaços
--      repetidos, a mesma regra de vendedores e geolocalização); UF em maiúsculas.
--      O CEP (prefixo de 5 dígitos) segue como texto para manter o zero à esquerda.
--      Toda correção fica marcada em dq_city_fixed.

CREATE OR REPLACE TABLE silver.customers AS
WITH latest_version AS (
    SELECT *
    FROM bronze.customers
    QUALIFY row_number() OVER (
        PARTITION BY customer_id
        ORDER BY _batch_id DESC, _source_file DESC, _row_hash
    ) = 1
),

standardized AS (
    SELECT
        customer_id,
        customer_unique_id,
        customer_zip_code_prefix,
        customer_city AS original_city,
        normalize_city(customer_city) AS customer_city,
        upper(trim(customer_state)) AS customer_state,
        _batch_id,
        _source_file
    FROM latest_version
)

SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    _batch_id,
    _source_file,
    coalesce(customer_city <> original_city, false) AS dq_city_fixed
FROM standardized;
