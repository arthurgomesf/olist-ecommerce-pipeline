-- Funções SQL da gold (rodam antes de todas as tabelas da camada).

-- Premissa de receita, definida em UM lugar só: venda concluída = pedido entregue.
-- Os pedidos "em andamento" (enviado, faturado, em separação...) ficam de fora: a maioria
-- está parada há mais de um ano no recorte dos dados, ou seja, provavelmente nunca foi
-- concluída. Cancelados e indisponíveis também não contam.
CREATE OR REPLACE MACRO is_completed_sale(order_status) AS
    order_status = 'delivered';

-- Região do Brasil a partir da UF (usada nas dimensões de cliente e vendedor).
CREATE OR REPLACE MACRO uf_region(uf) AS
    CASE
        WHEN uf IN ('AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO') THEN 'Norte'
        WHEN uf IN ('AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE') THEN 'Nordeste'
        WHEN uf IN ('DF', 'GO', 'MS', 'MT') THEN 'Centro-Oeste'
        WHEN uf IN ('ES', 'MG', 'RJ', 'SP') THEN 'Sudeste'
        WHEN uf IN ('PR', 'RS', 'SC') THEN 'Sul'
    END;
