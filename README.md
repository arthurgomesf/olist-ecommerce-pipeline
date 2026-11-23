# Olist E-commerce Pipeline

Pipeline ETL que transforma os dados públicos do marketplace brasileiro Olist em informação confiável
para o negócio: arquivos CSV brutos → camadas **bronze / silver / gold** em um mini Data Warehouse
**DuckDB** (modelo estrela) → análises em notebook, relatório em Markdown e dashboard Streamlit.

> 🚧 Em construção. As seções abaixo serão preenchidas ao longo do desenvolvimento.

## Sumário

1. Visão geral e arquitetura
2. Como executar do zero
3. Estrutura do repositório
4. Decisões de modelagem
5. Regras de qualidade
6. Premissas (definições de métricas)
7. Limitações dos dados
8. Análises
9. Uso de IA
10. Próximos passos

## Dados

Fonte: [Brazilian E-Commerce Public Dataset by Olist (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
— licença CC BY-NC-SA 4.0. Os CSVs **não** são versionados neste repositório; ficam em `data/raw/`.
