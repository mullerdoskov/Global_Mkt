"""
Engine SQLAlchemy e gerenciamento de sessões.
Pool configurado para produção (PostgreSQL).
"""

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import settings
from backend.db.schema import Base


def _create_engine():
    """Cria engine com configurações apropriadas para o tipo de banco."""
    url = settings.MARKET_DB_URL

    if "sqlite" in url:
        # SQLite: sem pool, check_same_thread=False
        engine = create_engine(
            url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    else:
        # PostgreSQL: pool otimizado
        engine = create_engine(
            url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return engine


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """Cria todas as tabelas no banco (CREATE IF NOT EXISTS)."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Remove todas as tabelas (CUIDADO — destrutivo)."""
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_session() -> Session:
    """Context manager que garante commit/rollback e close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """Dependency para FastAPI (yield pattern)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> dict:
    """Verifica se a conexão com o banco está funcional."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return {"status": "ok", "url": settings.MARKET_DB_URL.split("@")[-1]}
    except Exception as e:
        return {"status": "error", "error": str(e)}
