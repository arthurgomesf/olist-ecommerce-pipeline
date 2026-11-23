"""Configurações centrais do pipeline: caminhos e fontes de dados."""

from pathlib import Path

# Raiz do repositório (este arquivo fica em <raiz>/src/config.py).
# Tudo é relativo a ela, então o projeto roda em qualquer máquina/pasta.
ROOT_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT_DIR / "data" / "raw"  # CSVs originais, nunca alterados
WAREHOUSE_DIR = ROOT_DIR / "warehouse"
DB_PATH = WAREHOUSE_DIR / "olist.duckdb"  # o mini Data Warehouse (um único arquivo)

# Tabela da bronze -> prefixo do nome do arquivo na raw.
# Todo arquivo "<prefixo>*.csv" é tratado como um lote dessa tabela. Assim, um arquivo
# novo (ex.: olist_orders_dataset_2018-11.csv) é carregado sem nenhuma mudança no código.
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
