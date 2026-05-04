"""alembic/env.py — Market Data Platform.

Lê `MARKET_DB_URL` diretamente do ambiente (mesmo contrato de
`backend/db/connection.py` desde ISSUE-004). Não importa
`backend.db.connection` para evitar ativar o engine global / pool no
processo do alembic — só `Base.metadata` é necessária aqui.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Garante que o pacote `backend` esteja importável quando o alembic é
# invocado a partir da raiz de `market_platform_unified/`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Carrega .env se houver — mesmo comportamento do backend.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # python-dotenv pode estar ausente em ambientes mínimos
    pass

from backend.db.schema import Base  # noqa: E402  (após sys.path / load_dotenv)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    """Resolve via env → CSV externo → erro (mesmo contrato que o backend).

    Delega para `backend.config.credentials.resolve_database_url` (ISSUE-026)
    para que `alembic upgrade head` rode sem `MARKET_DB_URL` no env quando
    o CSV em `<Documents>/Cred/8.CREDENCIAIS/2.DB/` existir.
    """
    from backend.config.credentials import resolve_database_url

    return resolve_database_url()


def run_migrations_offline() -> None:
    """Modo offline — emite SQL sem conectar."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online — conecta ao banco e aplica."""
    url = _get_database_url()
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = url

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=url.startswith("sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
