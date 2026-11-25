"""Testes do portão de qualidade: uma checagem com violação precisa parar o pipeline, e a
gold nova (quebrada) não pode ser publicada."""

import pytest

from src.checks import DataCheckError, run_checks
from src.pipeline import transaction

CHECK = (
    "SELECT 'T-01' AS check_id, 'x nunca negativo' AS description, "
    "(SELECT count(*) FROM t WHERE x < 0) AS failures"
)


def test_checagem_com_violacao_interrompe_o_pipeline(con, tmp_path):
    con.execute("CREATE TABLE t AS SELECT * FROM (VALUES (1), (-5)) AS v(x)")
    checks_file = tmp_path / "checks.sql"
    checks_file.write_text(CHECK, encoding="utf-8")

    with pytest.raises(DataCheckError, match="T-01"):
        run_checks(con, batch_id=1, path=checks_file)

    # Mesmo falhando, o resultado fica registrado no log para investigação.
    assert con.execute("SELECT check_id, failures FROM audit.check_log").fetchall() == [
        ("T-01", 1)
    ]


def test_violacao_desfaz_a_tabela_nova_e_mantem_a_anterior(con, tmp_path):
    # Como no pipeline: a tabela é recriada e conferida dentro de uma transação.
    # Antes disso, já existe uma versão válida publicada.
    con.execute("CREATE TABLE t AS SELECT * FROM (VALUES (1), (5)) AS v(x)")
    checks_file = tmp_path / "checks.sql"
    checks_file.write_text(CHECK, encoding="utf-8")

    with pytest.raises(DataCheckError, match="T-01"), transaction(con):
        con.execute(
            "CREATE OR REPLACE TABLE t AS SELECT * FROM (VALUES (1), (-5)) AS v(x)"
        )
        run_checks(con, batch_id=2, path=checks_file)

    # A versão quebrada foi desfeita: continua valendo a anterior...
    assert con.execute("SELECT x FROM t ORDER BY x").fetchall() == [(1,), (5,)]
    # ...e a falha ficou registrada no log, mesmo com o rollback.
    assert con.execute(
        "SELECT batch_id, check_id, failures FROM audit.check_log"
    ).fetchall() == [(2, "T-01", 1)]


def test_checagem_sem_violacao_passa(con, tmp_path):
    con.execute("CREATE TABLE t AS SELECT * FROM (VALUES (1), (5)) AS v(x)")
    checks_file = tmp_path / "checks.sql"
    checks_file.write_text(CHECK, encoding="utf-8")

    run_checks(con, batch_id=1, path=checks_file)  # não pode levantar erro

    assert con.execute("SELECT check_id, failures FROM audit.check_log").fetchall() == [
        ("T-01", 0)
    ]
