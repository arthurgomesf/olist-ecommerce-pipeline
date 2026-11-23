"""Testes do portão de qualidade: uma checagem com violação precisa parar o pipeline."""

import pytest

from src.checks import DataCheckError, run_checks

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


def test_checagem_sem_violacao_passa(con, tmp_path):
    con.execute("CREATE TABLE t AS SELECT * FROM (VALUES (1), (5)) AS v(x)")
    checks_file = tmp_path / "checks.sql"
    checks_file.write_text(CHECK, encoding="utf-8")

    run_checks(con, batch_id=1, path=checks_file)  # não pode levantar erro

    assert con.execute("SELECT check_id, failures FROM audit.check_log").fetchall() == [
        ("T-01", 0)
    ]
