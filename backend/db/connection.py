"""
db/connection.py
Engine SQLAlchemy + pool de conexões.
Suporta PostgreSQL (produção) e SQLite (desenvolvimento/testes).
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

DATABASE_URL = os.getenv(
    "MARKET_DB_URL",
    "postgresql+psycopg2://postgres:141592@localhost:5432/market_db"
)

IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    # Habilita foreign keys para SQLite (WAL habilitado se suportado)
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass  # WAL pode não ser suportado em alguns filesystems
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Retorna uma sessão do banco. Usar com context manager."""
    return SessionLocal()


def test_connection() -> bool:
    """Testa a conexão com o banco de dados."""
    try:
        with engine.connect() as conn:
            if IS_SQLITE:
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
