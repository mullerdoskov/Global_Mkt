"""tests/test_alembic_migration.py
Valida ISSUE-009 — alembic upgrade head/downgrade base/upgrade head produz
o conjunto esperado de tabelas a partir de um SQLite vazio.

Estratégia: cada teste cria seu próprio arquivo SQLite em tempdir e roda
os comandos de alembic via API programática (`alembic.command`), sem
shell. Mantém isolamento total entre testes e do banco real configurado
em `conftest.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


REPO_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI = REPO_ROOT / "alembic.ini"

# Tabelas declaradas em backend/db/schema.py (excluindo alembic_version,
# que a própria ferramenta cria).
EXPECTED_TABLES = {
    "countries",
    "sectors_gics",
    "companies",
    "assets",
    "trading_calendar",
    "prices_daily",
    "financial_statements",
    "valuation_multiples",
    "ingestion_log",
}


def _make_config(db_url: str) -> Config:
    """Configuração de alembic apontando para um SQLite isolado."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    # env.py lê MARKET_DB_URL do ambiente; o caller já setou o monkeypatch.
    return cfg


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Banco SQLite vazio + MARKET_DB_URL monkeypatched para apontar nele."""
    db_path = tmp_path / "alembic_test.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("MARKET_DB_URL", url)
    return url


class TestAlembicUpgrade:
    def test_upgrade_head_cria_todas_as_tabelas(self, fresh_db):
        cfg = _make_config(fresh_db)
        command.upgrade(cfg, "head")

        engine = create_engine(fresh_db)
        try:
            tables = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

        assert EXPECTED_TABLES.issubset(tables), (
            f"Tabelas faltando: {EXPECTED_TABLES - tables}"
        )
        assert "alembic_version" in tables

    def test_round_trip_upgrade_downgrade_upgrade(self, fresh_db):
        cfg = _make_config(fresh_db)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")

        engine = create_engine(fresh_db)
        try:
            after_downgrade = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

        # Após downgrade base só sobra a tabela de versão do próprio alembic.
        assert after_downgrade == {"alembic_version"}, (
            f"Downgrade não limpou tudo: sobrou {after_downgrade - {'alembic_version'}}"
        )

        # Re-upgrade não pode falhar (regressão de ENUM órfão em Postgres).
        command.upgrade(cfg, "head")

        engine = create_engine(fresh_db)
        try:
            after_reupgrade = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

        assert EXPECTED_TABLES.issubset(after_reupgrade)

    def test_no_drift_entre_metadata_e_migration_head(self, fresh_db):
        """Garante que `Base.metadata` (schema.py) == cabeça das migrações.

        Se alguém alterar `backend/db/schema.py` sem gerar nova migração,
        este teste falha com "new upgrade operations detected" implícito —
        o autogenerate compararia metadata contra DB já em head e
        encontraria diferenças.
        """
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext

        from backend.db.schema import Base

        cfg = _make_config(fresh_db)
        command.upgrade(cfg, "head")

        engine = create_engine(fresh_db)
        try:
            with engine.connect() as conn:
                ctx = MigrationContext.configure(
                    conn,
                    opts={"compare_type": True, "compare_server_default": True},
                )
                diff = compare_metadata(ctx, Base.metadata)
        finally:
            engine.dispose()

        # `diff` lista operações que o autogenerate proporia. Filtrar
        # diferenças triviais que SQLite introduz vs. PostgreSQL (e.g.,
        # tipos ENUM tratados como CHECK constraints). O esperado é zero
        # operações estruturais (add/remove table/column/index/unique).
        structural = [
            op for op in diff
            if not (isinstance(op, tuple) and op and op[0] in {
                "modify_default",
                "modify_nullable",
                "modify_type",
            })
        ]
        assert not structural, (
            "Drift entre Base.metadata e alembic head — gere nova migração: "
            f"{structural}"
        )
