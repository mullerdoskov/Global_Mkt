"""
tests/test_no_import_side_effects.py
ISSUE-014 — importar módulos do backend não pode disparar trabalho colateral.

Antes desta issue:
- `backend.db.connection` chamava `load_dotenv()`, resolvia `MARKET_DB_URL` e
  rodava `create_engine(...)` em escopo de import — ou seja, importar o módulo
  podia falhar com `RuntimeError` se a env var não estivesse setada, mesmo
  para callers que só queriam ler `_resolve_database_url`.
- `backend.config.logging_config` executava `logger = setup_logging()` no fim
  do módulo, criando o diretório `logs/` e abrindo file handler antes que
  qualquer caller tivesse pedido um logger.
- `backend.api._cache` chamava `init_cache_sync()` em escopo de import,
  registrando backend global no singleton `FastAPICache`.

Depois desta issue:
- `connection.py`: `get_engine()`/`get_sessionmaker()` cacheados via lru_cache;
  importar é no-op (atributos como `engine`, `IS_SQLITE`, `SessionLocal`,
  `DATABASE_URL` resolvem on demand via `__getattr__`).
- `logging_config.py`: módulo só define funções; `setup_logging()` continua
  idempotente, e `get_logger(name)` é o ponto de entrada recomendado.
- `_cache.py`: side effect de import removido; uma fixture autouse em
  `conftest.py` instala o backend para os testes, lifespan instala em prod.

Estes testes garantem que os 3 módulos podem ser carregados em isolamento
SEM realizar nenhuma das operações acima.
"""

import importlib
import logging
import os
import sys

import pytest


def _purge_module(name: str) -> None:
    """Remove o módulo e seus filhos do sys.modules para forçar reimport."""
    for mod_name in list(sys.modules.keys()):
        if mod_name == name or mod_name.startswith(name + "."):
            sys.modules.pop(mod_name, None)


# ════════════════════════════════════════════════════════════════════
# 1. backend.db.connection
# ════════════════════════════════════════════════════════════════════


class TestConnectionImportSideEffects:
    def test_import_sem_market_db_url_nao_levanta(self, monkeypatch):
        """Antes de ISSUE-014: `import backend.db.connection` levantava
        `RuntimeError` se `MARKET_DB_URL` não estivesse setada (porque a
        resolução era em escopo de módulo).

        Depois: import é no-op; o erro só aparece se alguém invocar
        `_resolve_database_url()`, `get_engine()`, ou ler um atributo
        lazy (`engine`, `IS_SQLITE`, etc.).

        Detalhe técnico: usamos `setenv("", "")` em vez de `delenv` porque
        `_resolve_database_url` chama `_load_dotenv_once()`, que poderia
        relê-la do `.env` real do dev. Empty string passa pelo
        `load_dotenv` (que não sobrescreve vars existentes) e ainda casa
        com o guard `if not url:` — o caminho de erro alvo do teste.
        """
        # Limpa o cache do load_dotenv para que monkeypatch acima tenha efeito
        # mesmo que outro teste já tenha rodado a função.
        _purge_module("backend.db.connection")
        monkeypatch.setenv("MARKET_DB_URL", "")

        # Não deve levantar.
        mod = importlib.import_module("backend.db.connection")
        assert mod is not None
        # Garante que o cache de dotenv do módulo recém-importado começa zerado
        # — outros testes deste arquivo já rodaram `_load_dotenv_once` no
        # módulo anterior (purgado), mas o nosso é fresh.
        mod._load_dotenv_once.cache_clear()
        # Patch direto na função importada lazy dentro de `_load_dotenv_once`:
        # se `dotenv` carregar do `.env`, vai reescrever MARKET_DB_URL. Para
        # testar o caminho "ausente", anulamos o load_dotenv.
        import dotenv as _dotenv_mod
        monkeypatch.setattr(_dotenv_mod, "load_dotenv", lambda *a, **kw: False)

        # Mas tentar ler `engine` AGORA deve levantar — o erro foi adiado,
        # não eliminado.
        with pytest.raises(RuntimeError, match="MARKET_DB_URL"):
            _ = mod.engine

    def test_import_nao_chama_create_engine(self, monkeypatch):
        """Verifica que `create_engine` da SQLAlchemy não é invocado pelo
        mero import. Substituímos por um spy antes do import."""
        monkeypatch.setenv("MARKET_DB_URL", "sqlite:///:memory:")
        _purge_module("backend.db.connection")

        from sqlalchemy import create_engine as real_create_engine

        calls: list = []

        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return real_create_engine(*args, **kwargs)

        # Patch antes do import; o módulo importa `create_engine` por nome
        # do `sqlalchemy`, então patcheamos lá.
        monkeypatch.setattr("sqlalchemy.create_engine", spy)

        importlib.import_module("backend.db.connection")
        assert calls == [], (
            f"create_engine foi chamado em escopo de import "
            f"({len(calls)} vezes); ISSUE-014 regrediu"
        )

    def test_get_engine_cacheado(self, monkeypatch):
        monkeypatch.setenv("MARKET_DB_URL", "sqlite:///:memory:")
        _purge_module("backend.db.connection")
        mod = importlib.import_module("backend.db.connection")

        e1 = mod.get_engine()
        e2 = mod.get_engine()
        assert e1 is e2, "get_engine() deveria ser singleton via lru_cache"

    def test_lazy_attrs_funcionam(self, monkeypatch):
        monkeypatch.setenv("MARKET_DB_URL", "sqlite:///:memory:")
        _purge_module("backend.db.connection")
        mod = importlib.import_module("backend.db.connection")

        # `engine`, `IS_SQLITE`, `SessionLocal`, `DATABASE_URL` resolvem via
        # __getattr__ — o caller do código existente continua funcionando.
        engine = mod.engine
        assert engine is mod.get_engine()
        assert mod.IS_SQLITE is True  # URL começa com sqlite
        assert mod.DATABASE_URL == "sqlite:///:memory:"
        sm = mod.SessionLocal
        assert sm is mod.get_sessionmaker()

    def test_attr_inexistente_levanta(self, monkeypatch):
        monkeypatch.setenv("MARKET_DB_URL", "sqlite:///:memory:")
        _purge_module("backend.db.connection")
        mod = importlib.import_module("backend.db.connection")

        with pytest.raises(AttributeError):
            _ = mod.atributo_que_nao_existe


# ════════════════════════════════════════════════════════════════════
# 2. backend.config.logging_config
# ════════════════════════════════════════════════════════════════════


class TestLoggingConfigImportSideEffects:
    def test_import_nao_cria_logs_dir(self, tmp_path, monkeypatch):
        """Antes: `logger = setup_logging()` no fim do módulo criava o
        diretório `logs/` e abria handler em arquivo no momento do import.

        Depois: o módulo só define funções; o `os.makedirs` só roda quando
        alguém chama `setup_logging()` ou `get_logger()`.
        """
        # Aponta LOG_DIR para tmp_path/logs antes do import; verifica que NÃO
        # foi criado.
        target = tmp_path / "logs_dir_que_nao_deve_ser_criado"

        _purge_module("backend.config.logging_config")
        # Patch direto no atributo do módulo após import — mas precisamos
        # primeiro impedir o makedirs antigo. Estratégia: spy em os.makedirs.
        calls: list = []
        real_makedirs = os.makedirs

        def spy_makedirs(path, *args, **kwargs):
            calls.append(path)
            return real_makedirs(path, *args, **kwargs)

        monkeypatch.setattr("os.makedirs", spy_makedirs)

        importlib.import_module("backend.config.logging_config")
        # Não deve ter chamado makedirs durante o import.
        assert calls == [], (
            f"os.makedirs foi chamado em escopo de import "
            f"({calls}); ISSUE-014 regrediu"
        )
        assert not target.exists()

    def test_import_nao_adiciona_handlers(self):
        """Antes: o logger raiz `market_platform` ganhava 2 handlers
        (StreamHandler + RotatingFileHandler) durante o import. Depois:
        zero handlers até alguém chamar `setup_logging()`/`get_logger()`."""
        # Limpa o logger antes do import para isolar.
        target = logging.getLogger("market_platform")
        for h in list(target.handlers):
            target.removeHandler(h)

        _purge_module("backend.config.logging_config")
        importlib.import_module("backend.config.logging_config")

        target = logging.getLogger("market_platform")
        assert target.handlers == [], (
            f"logger 'market_platform' ganhou handlers no import "
            f"({target.handlers}); ISSUE-014 regrediu"
        )

    def test_setup_logging_idempotente(self, tmp_path, monkeypatch):
        """Garante que múltiplas chamadas a `setup_logging()` não duplicam
        handlers — propriedade essencial para que o uso em app.py + cli.py
        não cause logs duplicados."""
        # Redireciona LOG_DIR/LOG_FILE para tmp_path para não poluir o repo.
        _purge_module("backend.config.logging_config")
        mod = importlib.import_module("backend.config.logging_config")

        target_dir = tmp_path / "logs"
        monkeypatch.setattr(mod, "LOG_DIR", str(target_dir))
        monkeypatch.setattr(mod, "LOG_FILE", str(target_dir / "test.log"))

        # Limpa handlers preexistentes (de outros testes).
        target = logging.getLogger("market_platform")
        for h in list(target.handlers):
            target.removeHandler(h)

        l1 = mod.setup_logging()
        n1 = len(l1.handlers)
        l2 = mod.setup_logging()
        n2 = len(l2.handlers)
        l3 = mod.setup_logging()
        n3 = len(l3.handlers)

        assert l1 is l2 is l3
        assert n1 == n2 == n3 == 2, (
            f"esperado 2 handlers (stdout + arquivo) constantes, "
            f"got {n1}, {n2}, {n3}"
        )

    def test_get_logger_retorna_market_platform_ou_child(self, tmp_path, monkeypatch):
        _purge_module("backend.config.logging_config")
        mod = importlib.import_module("backend.config.logging_config")

        # Redireciona o LOG_DIR para evitar criar `logs/` no repo durante
        # o teste.
        monkeypatch.setattr(mod, "LOG_DIR", str(tmp_path / "logs"))
        monkeypatch.setattr(mod, "LOG_FILE", str(tmp_path / "logs" / "t.log"))

        # Limpa handlers preexistentes.
        target = logging.getLogger("market_platform")
        for h in list(target.handlers):
            target.removeHandler(h)

        root = mod.get_logger()
        assert root.name == "market_platform"

        child = mod.get_logger("ingestion")
        assert child.name == "market_platform.ingestion"

        # Logger explícito "market_platform" devolve o mesmo objeto que sem
        # nome — comportamento esperado.
        assert mod.get_logger("market_platform") is root


# ════════════════════════════════════════════════════════════════════
# 3. backend.api._cache
# ════════════════════════════════════════════════════════════════════


class TestCacheImportSideEffects:
    def test_import_nao_chama_init(self, monkeypatch):
        """Antes: `init_cache_sync()` rodava em escopo de import, mexendo no
        singleton `FastAPICache` global. Depois: o módulo só define funções
        — a inicialização passa pelo lifespan (prod) ou por fixture
        autouse (testes)."""
        from fastapi_cache import FastAPICache

        # Reset do estado global antes do teste, para que o asserção `_init`
        # tenha significado.
        FastAPICache.reset()
        assert not FastAPICache._init  # type: ignore[attr-defined]

        _purge_module("backend.api._cache")
        importlib.import_module("backend.api._cache")

        # Reimport NÃO deve ter inicializado o singleton.
        assert not FastAPICache._init, (  # type: ignore[attr-defined]
            "FastAPICache foi inicializado em escopo de import de "
            "_cache.py; ISSUE-014 regrediu"
        )

        # Restaura o estado para os testes seguintes — o conftest autouse
        # roda só uma vez (session-scope), então precisamos re-inicializar
        # manualmente após este teste.
        from backend.api._cache import init_cache_sync
        init_cache_sync()
