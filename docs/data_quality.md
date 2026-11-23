# Regras de qualidade

> Arquivo gerado automaticamente pelo pipeline (`python -m src.pipeline`) a partir
> da tabela `audit.quality_log`. Não edite à mão: as contagens são as da última execução.

## Como ler

| Ação | O que significa |
|---|---|
| remover | a linha sai da silver (continua guardada na bronze) |
| corrigir | o valor é ajustado; a correção fica marcada numa flag `dq_*` |
| sinalizar | a linha fica, marcada com uma flag `dq_*` para as análises decidirem |
| manter | nada muda; o caso fica registrado para transparência |

## Volumes por tabela

| Tabela | Linhas na bronze | Linhas na silver |
|---|---:|---:|
| orders | 99.441 | 99.441 |
| order_items | 112.650 | 112.650 |
| order_payments | 103.886 | 103.883 |
| order_reviews | 99.224 | 98.673 |
| customers | 99.441 | 99.441 |
| geolocation | 1.000.163 | 19.011 |
| sellers | 3.095 | 3.095 |
| products | 32.951 | 32.951 |

## Regras por tabela

### orders

| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |
|---|---|---|---:|---|
| ORD-01 | Versões antigas do mesmo pedido descartadas | remover | 0 | A bronze guarda todas as versões recebidas; vale a mais recente |
| ORD-02 | Datas em formato inválido convertidas para nulo | corrigir | 0 | Datas chegam como texto; o que não for data válida vira nulo em vez de quebrar a carga |
| ORD-03 | Pedido entregue (delivered) sem data de entrega | sinalizar | 8 | Sem a data não há como medir prazo; fica fora das métricas de entrega |
| ORD-04 | Pedido com data de entrega, mas status diferente de delivered | sinalizar | 6 | O status é a fonte da verdade; fica fora das métricas de entrega |
| ORD-05 | Pedido entregue sem data de aprovação do pagamento | sinalizar | 14 | Não afeta o prazo (compra -> entrega); mantido e marcado |
| ORD-06 | Coleta pela transportadora registrada antes da compra | sinalizar | 166 | Erro de registro na data de coleta; não afeta o prazo compra -> entrega |
| ORD-07 | Entrega ao cliente registrada antes da coleta pela transportadora | sinalizar | 23 | Datas intermediárias inconsistentes; o prazo compra -> entrega continua válido |
| ORD-08 | Pedido parado em status intermediário há mais de 6 meses (da última compra da base) | manter | 1.406 | Enviado/faturado/em separação há tanto tempo provavelmente nunca foi concluído; fica fora da receita |

### order_items

| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |
|---|---|---|---:|---|
| ITM-01 | Versões antigas do mesmo item descartadas | remover | 0 | A bronze guarda todas as versões recebidas; vale a mais recente |
| ITM-02 | Números e datas em formato inválido convertidos para nulo | corrigir | 0 | Valores chegam como texto; o que não for número ou data válida vira nulo |
| ITM-03 | Preço fora da faixa esperada (zero/negativo ou acima de R$ 10.000) | sinalizar | 0 | O maior preço do histórico é R$ 6.735; valor fora da faixa precisa de verificação |
| ITM-04 | Data-limite de envio mais de 1 ano após a compra | sinalizar | 4 | No histórico a mediana é 6 dias; mais de 1 ano é erro de registro. Coluna não usada nas análises |
| ITM-05 | Itens com frete zero | manter | 383 | Frete grátis é plausível (promoção); mantido e registrado para transparência |

### order_payments

| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |
|---|---|---|---:|---|
| PAY-01 | Versões antigas do mesmo pagamento descartadas | remover | 0 | A bronze guarda todas as versões recebidas; vale a mais recente |
| PAY-02 | Números em formato inválido convertidos para nulo | corrigir | 0 | Valores chegam como texto; o que não for número válido vira nulo |
| PAY-03 | Pagamentos do tipo not_defined com valor zero removidos | remover | 3 | Sem tipo e sem valor não é pagamento de fato; as linhas seguem guardadas na bronze |
| PAY-04 | Pagamentos com 0 parcelas corrigidos para 1 | corrigir | 2 | Todo pagamento tem ao menos uma parcela; marcado em dq_installments_fixed |
| PAY-05 | Pedidos sem nenhum pagamento | manter | 4 | Pedido segue válido; o total pago fica vazio. Receita é calculada pelos itens |
| PAY-06 | Pedidos cujo total pago difere de itens + frete em mais de R$ 0,01 | manter | 303 | Juros de parcelamento e vouchers explicam a diferença; por isso a receita vem dos itens |

### order_reviews

| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |
|---|---|---|---:|---|
| REV-01 | Versões antigas da mesma avaliação descartadas | remover | 0 | A bronze guarda todas as versões recebidas; vale a mais recente |
| REV-02 | Notas e datas em formato inválido convertidas para nulo | corrigir | 0 | Valores chegam como texto; o que não for número ou data válida vira nulo |
| REV-03 | Avaliações extras do mesmo pedido descartadas (fica a respondida por último) | remover | 551 | Uma nota por pedido evita contar o pedido duas vezes; a mais recente é a opinião atual |
| REV-04 | Comentários só com espaços ou quebras de linha convertidos para nulo | corrigir | 29 | Texto vazio não é comentário; padroniza a ausência de comentário como nulo |
| REV-05 | Avaliações sem comentário escrito | manter | 57.925 | O comentário é opcional; a nota (campo usado nas análises) está sempre preenchida |
| REV-06 | Pedidos sem nenhuma avaliação | manter | 768 | Avaliar é opcional; esses pedidos ficam fora das análises de satisfação |

### customers

| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |
|---|---|---|---:|---|
| CUS-01 | Versões antigas do mesmo customer_id descartadas | remover | 0 | A bronze guarda todas as versões recebidas; vale a mais recente |
| CUS-02 | Cidade padronizada (minúsculas, sem acento, sem espaços repetidos) | corrigir | 0 | Mesma cidade escrita de jeitos diferentes viraria cidades diferentes nas análises |
| CUS-03 | Mesmo cliente (customer_unique_id) com vários customer_id | manter | 2.997 | Esperado: o customer_id é gerado a cada pedido. Clientes e recompra usam customer_unique_id |
| CUS-04 | Clientes cuja UF diverge da UF do CEP (verificação) | manter | 0 | A UF do cliente vem do sistema, não é digitada; se bate com o CEP, as análises por estado são confiáveis |

### geolocation

| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |
|---|---|---|---:|---|
| GEO-01 | Pontos duplicados exatos removidos | remover | 261.831 | O mesmo ponto repetido não traz informação e distorceria a consolidação |
| GEO-02 | Pontos fora do território brasileiro (ou sem coordenada válida) descartados | remover | 27 | Erros de geocodificação (ex.: coordenadas no México ou em Portugal) puxariam a média do CEP |
| GEO-03 | Cidade padronizada (minúsculas, sem acento, sem espaços repetidos) | corrigir | 63.443 | A mesma cidade aparecia com e sem acento (ex.: "são paulo" e "sao paulo") |
| GEO-04 | CEPs de clientes ou vendedores ausentes da base de geolocalização | manter | 163 | Ficam sem coordenadas; cidade e UF continuam vindo do próprio cadastro |

### sellers

| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |
|---|---|---|---:|---|
| SEL-01 | Versões antigas do mesmo vendedor descartadas | remover | 0 | A bronze guarda todas as versões recebidas; vale a mais recente |
| SEL-02 | Texto da cidade padronizado (acento, espaços, UF e textos extras removidos) | corrigir | 30 | A cidade é digitada livremente (ex.: "sao paulo / sao paulo", "lages - sc") |
| SEL-03 | UF digitada diferente da UF do CEP: vale a UF do CEP | corrigir | 35 | O CEP é validado e a UF é digitada; o cadastro parece vir com "SP" por padrão |
| SEL-04 | Cidade inexistente na base de CEPs da UF substituída pela cidade do CEP | corrigir | 52 | Erros de digitação, abreviações ("sbc"), bairros, nome do estado ou texto inválido |

### products

| Regra | O que foi feito | Ação | Linhas afetadas | Por quê |
|---|---|---|---:|---|
| PRD-01 | Versões antigas do mesmo produto descartadas | remover | 0 | A bronze guarda todas as versões recebidas; vale a mais recente |
| PRD-02 | Medidas em formato inválido convertidas para nulo | corrigir | 0 | Valores chegam como texto; o que não for número inteiro válido vira nulo |
| PRD-03 | Produto sem categoria recebe o rótulo sem_categoria / unknown | corrigir | 610 | Cadastro incompleto (sem nome e fotos também); o rótulo evita perder a receita na análise |
| PRD-04 | Categoria ausente do arquivo oficial de tradução traduzida manualmente | corrigir | 13 | pc_gamer e portateis_cozinha_e_preparadores_de_alimentos não têm tradução oficial |
| PRD-05 | Categoria sem nenhuma tradução (mantida em português) | sinalizar | 0 | Categoria nova sem tradução: precisa ser incluída na tradução manual |
| PRD-06 | Peso zero convertido para nulo | corrigir | 4 | Nenhum produto pesa 0 g; é erro de cadastro, então o peso fica desconhecido |

## Checagens de integridade da gold

Rodam a cada execução, depois da gold. Se alguma encontrar violações, o pipeline para
com erro e esta documentação não é gerada.

| Checagem | O que é verificado | Violações |
|---|---|---:|
| CHK-01 | dim_date: date_day único e preenchido | 0 |
| CHK-02 | dim_customer: customer_id único e preenchido | 0 |
| CHK-03 | dim_seller: seller_id único e preenchido | 0 |
| CHK-04 | dim_product: product_id único e preenchido | 0 |
| CHK-05 | fct_orders: order_id único e preenchido | 0 |
| CHK-06 | fct_order_items: (order_id, order_item_id) único e preenchido | 0 |
| CHK-07 | fct_payments: (order_id, payment_sequential) único e preenchido | 0 |
| CHK-08 | fct_orders: todo customer_id existe em dim_customer | 0 |
| CHK-09 | fct_orders: toda data de compra existe em dim_date | 0 |
| CHK-10 | fct_order_items: todo item pertence a um pedido de fct_orders | 0 |
| CHK-11 | fct_order_items: todo product_id existe em dim_product | 0 |
| CHK-12 | fct_order_items: todo seller_id existe em dim_seller | 0 |
| CHK-13 | fct_payments: todo pagamento pertence a um pedido de fct_orders | 0 |
| CHK-14 | fct_orders: nota da avaliação entre 1 e 5 | 0 |
| CHK-15 | fct_orders: prazo de entrega nunca negativo | 0 |
| CHK-16 | fct_order_items: preço maior que zero | 0 |
| CHK-17 | fct_payments: valor pago nunca negativo | 0 |
| CHK-18 | fct_orders tem exatamente os pedidos da silver | 0 |
| CHK-19 | Soma dos preços: fct_order_items = silver.order_items | 0 |
| CHK-20 | Soma dos itens por pedido: fct_orders = fct_order_items | 0 |
| CHK-21 | Soma dos pagamentos: fct_orders = fct_payments | 0 |
