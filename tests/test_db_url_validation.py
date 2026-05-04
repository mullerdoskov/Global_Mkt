"""
tests/test_db_url_validation.py
Valida ISSUE-004 — ausência de MARKET_DB_URL aborta com mensagem clara,
sem cair em fallback com credencial hardcoded.

ISSUE-026: agora há um fallback legítimo (CSV externo em
`<Documents>/Cred/8.CREDENCIAIS/2.DB/`). Os testes que validam o erro
de "env ausente" mockam o leitor do CSV para garantir que o caminho
de erro continua funcionando quando ambas as fontes faltam.
"""

import pytest

from backend.config import credentials as cred_module
from backend.db.connection import _resolve_database_url


@pytest.fixture
def sem_csv_fallback(monkeypatch):
    """Desabilita o fallback do CSV — força o teste a exercitar o caminho
    de erro do env-only.
    """
    monkeypatch.setattr(cred_module, "_read_cred_file", lambda: None)


class TestResolveDatabaseUrl:
    def test_retorna_url_quando_env_setada(self, monkeypatch):
        monkeypatch.setenv("MARKET_DB_URL", "sqlite:///./qualquer.db")
        assert _resolve_database_url() == "sqlite:///./qualquer.db"

    def test_levanta_runtime_error_quando_env_ausente(
        self, monkeypatch, sem_csv_fallback
    ):
        monkeypatch.delenv("MARKET_DB_URL", raising=False)
        with pytest.raises(RuntimeError, match="MARKET_DB_URL"):
            _resolve_database_url()

    def test_levanta_runtime_error_quando_env_vazia(
        self, monkeypatch, sem_csv_fallback
    ):
        monkeypatch.setenv("MARKET_DB_URL", "")
        with pytest.raises(RuntimeError, match="MARKET_DB_URL"):
            _resolve_database_url()

    def test_mensagem_de_erro_orienta_o_usuario(
        self, monkeypatch, sem_csv_fallback
    ):
        monkeypatch.delenv("MARKET_DB_URL", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            _resolve_database_url()
        msg = str(exc_info.value)
        assert "sqlite" in msg.lower()
        assert "postgresql" in msg.lower()
        # Mensagem nova (ISSUE-026) menciona o CSV externo em vez de `.env`.
        assert "Cred/8.CREDENCIAIS/2.DB" in msg

    def test_sem_credencial_hardcoded_no_codigo(self):
        """Garante que a senha vazada (ISSUE-004 / ISSUE-005) não voltou ao código.

        Escopo: somente a árvore oficial (`backend/`), excluindo o nested
        `Global_Mkt_2.0/` (responsabilidade de ISSUE-001, humano-only).
        """
        from pathlib import Path

        backend_dir = Path(__file__).resolve().parent.parent / "backend"
        nested = backend_dir / "Global_Mkt_2.0"
        offending = "141592"
        for py_file in backend_dir.rglob("*.py"):
            try:
                py_file.relative_to(nested)
                continue  # pula nested — fora de escopo de ISSUE-004
            except ValueError:
                pass
            content = py_file.read_text(encoding="utf-8")
            assert offending not in content, (
                f"Senha hardcoded '{offending}' detectada em {py_file}. "
                "Ver ISSUE-004."
            )
