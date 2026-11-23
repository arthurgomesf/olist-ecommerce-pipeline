"""Configurações centrais do pipeline: caminhos e fontes de dados."""

from pathlib import Path

# Raiz do repositório (este arquivo fica em <raiz>/src/config.py).
# Tudo é relativo a ela, então o projeto roda em qualquer máquina/pasta.
ROOT_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT_DIR / "data" / "raw"  # CSVs originais, nunca alterados
WAREHOUSE_DIR = ROOT_DIR / "warehouse"
DB_PATH = WAREHOUSE_DIR / "olist.duckdb"  # o mini Data Warehouse (um único arquivo)
SQL_DIR = ROOT_DIR / "sql"  # transformações (silver/gold) e regras de qualidade

# Tabela da bronze -> prefixo do nome do arquivo na raw.
# Todo arquivo "<prefixo>*.csv" é tratado como um lote dessa tabela. Assim, um arquivo
# novo (ex.: olist_orders_dataset_2018-11.csv) é carregado sem nenhuma mudança no código.
# Arquivos novos devem vir DEPOIS do original na ordem alfabética (ex.: sufixo com data):
# é assim que a silver sabe qual versão de um registro é a mais recente.
SOURCES = {
    "customers": "olist_customers_dataset",
    "geolocation": "olist_geolocation_dataset",
    "orders": "olist_orders_dataset",
    "order_items": "olist_order_items_dataset",
    "order_payments": "olist_order_payments_dataset",
    "order_reviews": "olist_order_reviews_dataset",
    "products": "olist_products_dataset",
    "sellers": "olist_sellers_dataset",
    "category_translation": "product_category_name_translation",
}

# Tabelas da silver, na ordem de construção. Cada uma tem dois arquivos:
#   sql/silver/<tabela>.sql   -> a transformação (limpeza, tipos, deduplicação)
#   sql/quality/<tabela>.sql  -> as regras de qualidade e quantas linhas cada uma afetou
SILVER_TABLES = [
    "orders",
    "order_items",
    "order_payments",
    "order_reviews",
    "customers",
    "geolocation",  # antes de sellers: a localização do vendedor é conferida pelo CEP
    "sellers",
    "products",
]
