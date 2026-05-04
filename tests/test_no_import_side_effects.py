"""
tests/test_no_import_side_effects.py
ISSUE-014 / ISSUE-024 — importar módulos do backend não pode disparar
trabalho colateral.

Antes destas issues:
- `backend.db.connection` chamava `load_dotenv()`, resolvia `MARKET_DB_URL` e
  rodava `create_engine(...)` em escopo de import — ou seja, importar o módulo
  podia falhar com `RuntimeError` se a env var não estivesse setada, mesmo
  para callers que só queriam ler `_resolve_database_url`.
- `backend.config.logging_config` executava `logger = setup_logging()` no fim
  do módulo, criando o diretório `logs/` e abrindo file handler antes que
  qualquer caller tivesse pedido um logger.
- `backend.api._cache` chamava `init_cache_sync()` em escopo de import,
  registrando backend global no singleton `FastAPICache`.
- `backend.app` chamava `setup_logging()` em escopo de módulo (linha 32) +
  emitia 5+ `logger.info(...)` no nível de import — fechando ISSUE-014 no
  papel mas mantendo o mesmo padrão na entry-point (`app.py`).

Depois destas issues:
- `connection.py`: `get_engine()`/`get_sessionmaker()` cacheados via lru_cache;
  importar é no-op (atributos como `engine`, `IS_SQLITE`, `SessionLocal`,
  `DATABASE_URL` resolvem on demand via `__getattr__`).
- `logging_config.py`: módulo só define funções; `setup_logging()` continua
  idempotente, e `get_logger(name)` é o ponto de entrada recomendado.
- `_cache.py`: side effect de import removido; uma fixture autouse em
  `conftest.py` instala o backend para os testes, lifespan instala em prod.
- `app.py` (ISSUE-024): `logger = logging.getLogger("market_platform")` em
  escopo de módulo (puro getattr, sem I/O); `setup_logging()` movido para o
  primeiro passo do lifespan; banner de boot encapsulado em
  `_log_startup_banner()` chamado pelo lifespan.

Estes testes garantem que os 4 módulos podem ser carregados em isolamento
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

        # ISSUE-026: também desabilitar o fallback do CSV externo, senão o
        # arquivo de credenciais do dev (`<Documents>/Cred/...`) atende a
        # request e o caminho de erro nunca dispara.
        from backend.config import credentials as _cred_mod
        monkeypatch.setattr(_cred_mod, "_read_cred_file", lambda: None)

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


# ════════════════════════════════════════════════════════════════════
# 4. backend.app  (ISSUE-024)
# ════════════════════════════════════════════════════════════════════


class TestAppImportSideEffects:
    """Antes de ISSUE-024:
    - `app.py:32` rodava `logger = setup_logging()`, criando `logs/` e abrindo
      RotatingFileHandler no momento do import.
    - 5+ `logger.info(...)` em escopo de módulo geravam I/O imediato (banner +
      CORS + rate limiting + frontend mount).

    Depois de ISSUE-024:
    - `logger = logging.getLogger("market_platform")` (sem setup, sem I/O).
    - `setup_logging()` movido para a primeira linha do lifespan.
    - Banner consolidado em `_log_startup_banner()`, também chamado pelo
      lifespan.
    """

    def _purge_app_chain(self) -> None:
        """Reset dos módulos que `backend.app` importa direta ou
        indiretamente, para que um reimport seja realmente fresh.

        Mantém `backend.config.logging_config` no `sys.modules` porque os
        testes deste arquivo (TestLoggingConfigImportSideEffects) já cobrem
        o módulo isoladamente; aqui queremos a interação `app.py` →
        `logging_config.setup_logging`, que existe assim que ambos estão
        em sys.modules.
        """
        _purge_module("backend.app")

    def test_import_nao_chama_setup_logging(self, monkeypatch):
        """Spy em `setup_logging` antes do import: módulo não pode invocá-la
        em escopo de import. ISSUE-024 desloca a chamada para o lifespan.
        """
        # Garante que `backend.config.logging_config` já está carregado
        # (foi pelos testes anteriores deste arquivo, ou via conftest).
        import backend.config.logging_config as logging_config

        calls: list = []

        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return logging.getLogger("market_platform")

        monkeypatch.setattr(logging_config, "setup_logging", spy)

        self._purge_app_chain()
        importlib.import_module("backend.app")

        assert calls == [], (
            f"setup_logging foi chamado em escopo de import de backend.app "
            f"({len(calls)} vezes); ISSUE-024 regrediu"
        )

    def test_import_nao_chama_makedirs_logs(self, monkeypatch):
        """`setup_logging` cria `logs/` via `os.makedirs`. Spy em
        `os.makedirs`: nenhuma chamada deve sair do import de backend.app.
        """
        calls: list = []
        real_makedirs = os.makedirs

        def spy_makedirs(path, *args, **kwargs):
            calls.append(str(path))
            return real_makedirs(path, *args, **kwargs)

        monkeypatch.setattr("os.makedirs", spy_makedirs)

        self._purge_app_chain()
        importlib.import_module("backend.app")

        # Aceitamos zero chamadas — qualquer makedirs seria evidência de
        # side effect (LOG_DIR ou outro caminho criado durante import).
        assert calls == [], (
            f"os.makedirs foi chamado durante import de backend.app: "
            f"{calls}; ISSUE-024 regrediu"
        )

    def test_import_nao_adiciona_handlers_no_logger(self, monkeypatch):
        """O logger `market_platform` não pode ganhar handlers durante o
        import de backend.app. Antes da issue, `setup_logging()` em module-
        level adicionava 2 handlers (StreamHandler + RotatingFileHandler).
        """
        # Limpa handlers preexistentes para isolar — outros testes
        # (test_setup_logging_idempotente, ou simplesmente pytest com
        # `-s`) podem ter deixado handlers.
        target = logging.getLogger("market_platform")
        original_handlers = list(target.handlers)
        for h in original_handlers:
            target.removeHandler(h)

        try:
            self._purge_app_chain()
            importlib.import_module("backend.app")

            # `from backend.config.logging_config import setup_logging` apenas
            # bind a função no namespace — não a executa. Logger fica sem
            # handlers.
            assert target.handlers == [], (
                f"logger 'market_platform' ganhou handlers durante import "
                f"de backend.app ({target.handlers}); ISSUE-024 regrediu"
            )
        finally:
            # Restaura handlers para os próximos testes (que podem usar
            # logging em assertions de smoke/integração).
            for h in original_handlers:
                target.addHandler(h)

    def test_logger_no_module_e_getlogger_puro(self):
        """Garante que o `logger` exportado por backend.app é o resultado
        de `logging.getLogger("market_platform")` puro — sem qualquer
        configuração extra. Assim, alterar handlers a partir de
        `setup_logging()` (via lifespan) afeta o mesmo objeto.
        """
        self._purge_app_chain()
        mod = importlib.import_module("backend.app")

        assert mod.logger is logging.getLogger("market_platform"), (
            "backend.app.logger deveria ser o logger root do projeto, "
            "obtido via logging.getLogger('market_platform') sem chamar "
            "setup_logging em escopo de import"
        )

    def test_log_startup_banner_emite_linhas_esperadas(self, monkeypatch):
        """Wiring do banner: chamar `_log_startup_banner()` (que o lifespan
        invoca depois de setup_logging) emite as 4 linhas-chave do estado
        de boot. Garante que mover as mensagens do module-level para o
        lifespan não derrubou o que o operador via no console.

        Substitui `mod.logger` por um Mock para evitar dependência de
        propagação/caplog/handler-state — o full-suite tem dezenas de
        TestClient lifespans rodando antes deste teste, mexendo nos
        handlers do logger global. Mock no nível do módulo é à prova de
        cross-test bleed.
        """
        from unittest.mock import MagicMock

        self._purge_app_chain()
        mod = importlib.import_module("backend.app")

        # Garante que cors_origins está populado (módulo já avaliou).
        assert isinstance(mod.cors_origins, list)

        fake_logger = MagicMock()
        monkeypatch.setattr(mod, "logger", fake_logger)

        mod._log_startup_banner()

        # Concatena (level, message) de cada chamada para inspeção.
        info_messages = [
            str(call.args[0]) for call in fake_logger.info.call_args_list
        ]
        warning_messages = [
            str(call.args[0]) for call in fake_logger.warning.call_args_list
        ]
        all_messages = info_messages + warning_messages

        assert any("Iniciando market_platform_unified backend" in m for m in info_messages), (
            f"banner de boot ausente em info()={info_messages}"
        )
        assert any("CORS habilitado" in m for m in info_messages), (
            f"linha de CORS ausente em info()={info_messages}"
        )
        assert any("Rate limiting" in m for m in info_messages), (
            f"linha de rate limiting ausente em info()={info_messages}"
        )
        # Frontend ou monta (info) ou avisa que diretório não existe (warning).
        assert any(
            ("Frontend estático montado" in m) or
            ("Diretório de frontend não encontrado" in m)
            for m in all_messages
        ), f"linha de frontend ausente em info()+warning()={all_messages}"
