"""
db/connection.py
Engine SQLAlchemy + pool de conexões — inicialização lazy.

ISSUE-014: importar este módulo é um no-op. `load_dotenv()`, resolução de
`MARKET_DB_URL`, `create_engine()` e `sessionmaker()` ficam dentro de
`get_engine()`/`get_sessionmaker()`, ambos cacheados via `functools.lru_cache`.
A primeira chamada faz o trabalho; as seguintes retornam o singleton.

Compatibilidade com `from backend.db.connection import engine, IS_SQLITE,
SessionLocal, DATABASE_URL`: implementada via PEP 562 (`__getattr__` em escopo
de módulo). Os atributos resolvem na primeira leitura e disparam `get_engine()`,
mas isso só ocorre quando algum caller efetivamente acessa o engine — não no
mero `import`.

Suporta PostgreSQL (produção) e SQLite (desenvolvimento/testes).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session


@lru_cache(maxsize=1)
def _load_dotenv_once() -> None:
    """Lê o `.env` uma única vez por processo. Idempotente.

    Chamado por `_resolve_database_url`; mantido fora de escopo de import para
    que importar este módulo não toque o filesystem nem altere `os.environ`.
    """
    from dotenv import load_dotenv  # import lazy: dotenv não é dep de testes
    load_dotenv()


def _resolve_database_url() -> str:
    """Lê `MARKET_DB_URL` do ambiente. Aborta com mensagem clara se ausente.

    Não há fallback: credenciais hardcoded violam PSCW e ISSUE-004.
    """
    _load_dotenv_once()
    url = os.getenv("MARKET_DB_URL")
    if not url:
        raise RuntimeError(
            "MARKET_DB_URL não está definida. "
            "Configure em .env ou variável de ambiente. Exemplos:\n"
            "  - sqlite:///market_db.sqlite (desenvolvimento)\n"
            "  - postgresql+psycopg2://USER:PASS@host:5432/dbname (produção)"
        )
    return url


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Retorna o engine SQLAlchemy do processo (singleton via lru_cache).

    Primeira chamada: resolve URL, cria engine e — se SQLite — registra o
    listener de `PRAGMA journal_mode=WAL` + `foreign_keys=ON`. Chamadas
    posteriores devolvem o mesmo objeto.

    Para descartar e recriar (ex.: testes que trocam `MARKET_DB_URL`):
    `get_engine.cache_clear()`.
    """
    url = _resolve_database_url()
    if _is_sqlite_url(url):
        engine = create_engine(
            url,
            echo=False,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass  # WAL pode não estar disponível em alguns filesystems
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker:
    """Retorna o `sessionmaker` do processo (singleton). Lazy."""
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def get_session() -> Session:
    """Retorna uma nova sessão do banco. Usar com context manager."""
    return get_sessionmaker()()


def is_sqlite() -> bool:
    """Verifica em runtime se o banco configurado é SQLite."""
    return _is_sqlite_url(_resolve_database_url())


def test_connection() -> bool:
    """Testa a conexão com o banco de dados."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            if is_sqlite():
                result = conn.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                print(f"✅ Conexão OK — SQLite: {version}")
            else:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                print(f"✅ Conexão OK — PostgreSQL: {version}")
            return True
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Compatibilidade com `from backend.db.connection import engine, IS_SQLITE, ...`
#
# PEP 562: `__getattr__` em escopo de módulo é chamado para nomes não definidos
# explicitamente. Resolve sob demanda — importar o módulo não dispara nada,
# mas qualquer leitura de `connection.engine` ou `connection.IS_SQLITE` força
# `get_engine()` a rodar. Mantém o contrato existente do codebase enquanto
# elimina os side effects do módulo (objetivo de ISSUE-014).
# ─────────────────────────────────────────────────────────────────────────────

_LAZY_ATTRS = {"engine", "IS_SQLITE", "SessionLocal", "DATABASE_URL"}


def __getattr__(name: str) -> Any:
    if name == "engine":
        return get_engine()
    if name == "IS_SQLITE":
        return is_sqlite()
    if name == "SessionLocal":
        return get_sessionmaker()
    if name == "DATABASE_URL":
        return _resolve_database_url()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_ATTRS))
