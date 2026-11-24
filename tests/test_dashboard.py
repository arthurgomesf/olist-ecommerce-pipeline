"""Teste de fumaça do dashboard: o app inteiro roda sem erro sobre o Data Warehouse real.

Precisa do pipeline já executado (warehouse/olist.duckdb); sem ele, o teste é pulado.
"""

import pytest
from streamlit.testing.v1 import AppTest

from src.config import DB_PATH, ROOT_DIR

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(), reason="rode o pipeline antes: python -m src.pipeline"
)


def test_dashboard_roda_sem_erros():
    app = AppTest.from_file(
        str(ROOT_DIR / "app" / "dashboard.py"), default_timeout=60
    ).run()

    assert not app.exception
    assert len(app.tabs) == 5
    assert len(app.metric) >= 6  # indicadores do topo + os de cada aba
