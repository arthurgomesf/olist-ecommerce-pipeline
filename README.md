# Olist E-commerce Pipeline

Pipeline ETL que transforma os dados públicos do marketplace brasileiro **Olist** em informação
confiável para o negócio: os CSVs brutos passam pelas camadas **bronze → silver → gold** de um
mini Data Warehouse em **DuckDB** e alimentam análises em notebook, um relatório em Markdown e um
dashboard em Streamlit.

> 🚧 Em construção: as seções marcadas como _(em construção)_ serão concluídas nas próximas etapas.

## Sumário

1. [Visão geral e arquitetura](#1-visão-geral-e-arquitetura)
2. [Como executar do zero](#2-como-executar-do-zero)
3. [Estrutura do repositório](#3-estrutura-do-repositório)
4. [Decisões de modelagem](#4-decisões-de-modelagem)
5. [Regras de qualidade](#5-regras-de-qualidade)
6. [Premissas](#6-premissas)
7. [Limitações dos dados](#7-limitações-dos-dados)
8. [Análises](#8-análises)
9. [Uso de IA](#9-uso-de-ia)

## 1. Visão geral e arquitetura

```mermaid
flowchart LR
    raw["CSVs da Olist<br/>data/raw/"] -->|carga incremental<br/>por hash| bronze[("bronze")]
    bronze -->|limpeza, tipos e<br/>deduplicação| silver[("silver")]
    silver -->|modelo estrela| gold[("gold")]
    gold --> nb["Notebook +<br/>relatório"]
    gold --> app["Dashboard<br/>Streamlit"]
    silver -.->|regras de qualidade| audit[("audit")]
    audit -.-> dq["docs/data_quality.md"]
```

| Camada | O que guarda | Como é atualizada |
|---|---|---|
| **raw** (`data/raw/`) | Os CSVs originais, nunca alterados | Arquivos novos são acrescentados à pasta |
| **bronze** | Cópia fiel dos CSVs (tudo como texto) + colunas de controle | Só recebe inserções, controladas por hash |
| **silver** | Uma tabela limpa por entidade, com tipos corretos e flags de qualidade | Recalculada a partir da bronze a cada execução |
| **gold** | Modelo estrela pronto para análise _(em construção)_ | Recalculada a partir da silver |
| **audit** | Log de cargas e resultado das regras de qualidade | A cada execução |

Tudo roda localmente, sem servidor: o Data Warehouse é um único arquivo (`warehouse/olist.duckdb`).

## 2. Como executar do zero

**Pré-requisitos:** Python 3.11 ou superior (desenvolvido em 3.12) e Git.

1. **Clone o repositório e crie o ambiente virtual**

   ```powershell
   # Windows (PowerShell)
   git clone https://github.com/arthurgomesf/olist-ecommerce-pipeline.git
   cd olist-ecommerce-pipeline
   py -3.12 -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```

   ```bash
   # Linux / macOS
   git clone https://github.com/arthurgomesf/olist-ecommerce-pipeline.git
   cd olist-ecommerce-pipeline
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

2. **Baixe os dados** do [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
   (botão _Download_; o Kaggle pode pedir login) e extraia os **9 arquivos `.csv`** em `data/raw/`.
   Os dados não ficam no repositório (licença CC BY-NC-SA 4.0 e ~126 MB).

3. **Rode o pipeline** (no Linux/macOS, troque `.venv\Scripts\python` por `.venv/bin/python`):

   ```powershell
   .venv\Scripts\python -m src.pipeline
   ```

   O pipeline cria `warehouse/olist.duckdb`, mostra no log quantas linhas entraram em cada etapa e
   regenera `docs/data_quality.md`. Rodar de novo **não duplica nada** (ver seção 4).

4. **Rode os testes**

   ```powershell
   .venv\Scripts\python -m pytest
   ```

> Se o arquivo `warehouse/olist.duckdb` estiver aberto em outro programa (notebook, dashboard),
> o pipeline avisa e para: o DuckDB permite um único processo escrevendo no arquivo.

## 3. Estrutura do repositório

```
├── data/raw/              # CSVs originais (não versionados)
├── warehouse/             # olist.duckdb, gerado pelo pipeline (não versionado)
├── src/
│   ├── config.py          # caminhos e lista de fontes e tabelas
│   ├── bronze.py          # carga incremental CSV -> bronze
│   ├── transform.py       # executa os SQL de cada camada
│   ├── quality.py         # calcula e registra as regras de qualidade
│   ├── docs.py            # gera docs/data_quality.md
│   └── pipeline.py        # orquestra tudo: python -m src.pipeline
├── sql/
│   ├── silver/            # uma transformação por tabela (+ _functions.sql)
│   └── quality/           # as regras de qualidade de cada tabela
├── docs/
│   └── data_quality.md    # gerado automaticamente a cada execução
├── tests/                 # testes automatizados (pytest)
└── requirements.txt
```

## 4. Decisões de modelagem

**Por que DuckDB:** é um banco analítico (colunar) que roda dentro do Python, sem servidor: o
avaliador reproduz tudo com `pip install`. Lê CSV nativamente e tem SQL completo.

**Por que camadas:** a raw nunca é alterada, então qualquer resultado pode ser reconstruído e
auditado desde a origem; cada camada tem uma única responsabilidade.

### Bronze: carga incremental e fiel

- Cada CSV entra **como texto puro**: nenhuma conversão implícita (o CEP `01037` continua `01037`,
  com o zero à esquerda). Converter tipos é decisão explícita da silver.
- Cada linha recebe colunas de controle: `_row_hash` (md5 do conteúdo da linha), `_batch_id`,
  `_source_file` e `_ingested_at`.
- **Só entram linhas cujo hash ainda não existe.** Rodar o pipeline de novo não duplica nada, e um
  arquivo novo na raw (ex.: `olist_orders_dataset_2018-11.csv`) acrescenta só o que é novo ou mudou.
- Cada arquivo entra numa transação (tudo ou nada), e um arquivo com colunas diferentes das
  esperadas é recusado com erro, em vez de gravar dado errado.
- `audit.load_log` registra, por lote, as linhas lidas e inseridas de cada arquivo.

### Silver: uma tabela limpa por entidade

- **Versão mais recente** de cada registro pela chave de negócio (maior lote; dentro do mesmo lote,
  o arquivo que vem depois na ordem do nome). Em volume grande, a recalculação daria lugar a um
  `MERGE` só com os lotes novos.
- **Tipos explícitos** com `try_cast` (valor inválido vira nulo e é contado). Valores monetários em
  `DECIMAL(12,2)`: com ponto flutuante, 76 pedidos com diferença de exatamente R$ 0,01 entre o total
  pago e o total dos itens apareciam como divergentes por erro de arredondamento.
- **Sinalizar em vez de apagar:** problemas viram flags `dq_*`; só saem da silver duplicatas e
  registros sem informação. Nada se perde, porque a bronze guarda tudo.
- **Escolhas de grão:**
  - `order_reviews`: **uma avaliação por pedido** (a respondida por último), para nenhum pedido
    contar duas vezes na satisfação.
  - `customers`: o `customer_id` é gerado a cada pedido; **a pessoa é o `customer_unique_id`**
    (2.997 pessoas têm mais de um `customer_id`).
  - `geolocation`: **uma linha por prefixo de CEP**, com a mediana das coordenadas e a cidade mais
    frequente.
- **"O CEP manda" na localização do vendedor:** cidade e UF são digitadas pelo vendedor, o CEP é
  validado. Quando divergem, vale o CEP. O cadastro de vendedores parece vir com "SP" preenchido
  por padrão (quase todas as UFs corrigidas eram "SP"). Já a UF dos clientes não diverge do CEP em
  nenhum caso verificável (regra CUS-04), por isso as análises por estado do cliente são confiáveis.
- A mesma função `normalize_city()` padroniza cidades em clientes, vendedores e geolocalização,
  para que a comparação entre tabelas seja justa.

### Gold _(em construção)_

## 5. Regras de qualidade

Cada tabela da silver tem um arquivo em `sql/quality/` com as suas regras: o que foi feito, a ação
(remover, corrigir, sinalizar ou manter), o motivo e quantas linhas foram afetadas. O pipeline grava
o resultado em `audit.quality_log` e gera a lista completa, com as contagens, em
[`docs/data_quality.md`](docs/data_quality.md). Os números nunca são digitados à mão.

Os casos que mais mudam o dado:

- **Geolocalização:** 26% das linhas eram duplicatas exatas; pontos com coordenadas fora do Brasil
  (erros de geocodificação) são descartados, preservando Fernando de Noronha.
- **Avaliações:** pedidos com mais de uma avaliação ficam com a mais recente.
- **Produtos:** categoria traduzida para inglês, com tradução manual para as duas categorias que
  faltam no arquivo oficial; produtos sem categoria recebem o rótulo `unknown`, para que a receita
  deles não suma das análises por categoria.
- **Vendedores:** cidade padronizada e localização corrigida pelo CEP.
- **Pagamentos:** pagamentos sem tipo e sem valor são removidos; parcelas zeradas viram 1.

## 6. Premissas

Já fixadas na silver:

- **Cliente** é o `customer_unique_id`, não o `customer_id`.
- **Receita vem dos itens** (`price`), não dos pagamentos: o total pago inclui juros de parcelamento
  e vouchers e difere de itens + frete em parte dos pedidos.
- **Uma avaliação por pedido:** a respondida por último.
- **Localização do vendedor:** o CEP prevalece sobre a cidade e a UF digitadas.

_As definições das métricas (receita por status do pedido, atraso, tempo de entrega) serão fixadas
na etapa de análise (em construção)._

## 7. Limitações dos dados

- **Sem custo dos produtos nem comissão:** não há como calcular margem ou lucro; "receita" aqui é o
  valor de venda dos produtos no marketplace.
- **Dados anonimizados e só com o prefixo do CEP** (5 dígitos): a localização é aproximada, e parte
  dos CEPs de clientes e vendedores não existe na base de geolocalização.
- **Prefixos de CEP que cobrem mais de uma cidade:** a "cidade do CEP" é a mais frequente no prefixo.
  Por isso um vendedor de Monte Alegre do Sul (SP) passou a constar como Jaguariúna, a cidade vizinha.
- **Janela de 09/2016 a 10/2018**, com meses das pontas quase vazios.

_(lista em construção)_

## 8. Análises

_(em construção)_

## 9. Uso de IA

_(a ser escrito pelo autor)_
