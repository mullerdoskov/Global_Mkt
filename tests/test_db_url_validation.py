"""
tests/test_db_url_validation.py
Valida ISSUE-004 — ausência de MARKET_DB_URL aborta com mensagem clara,
sem cair em fallback com credencial hardcoded.
"""

import pytest

from backend.db.connection import _resolve_database_url


class TestResolveDatabaseUrl:
    def test_retorna_url_quando_env_setada(self, monkeypatch):
        monkeypatch.setenv("MARKET_DB_URL", "sqlite:///./qualquer.db")
        assert _resolve_database_url() == "sqlite:///./qualquer.db"

    def test_levanta_runtime_error_quando_env_ausente(self, monkeypatch):
        monkeypatch.delenv("MARKET_DB_URL", raising=False)
        with pytest.raises(RuntimeError, match="MARKET_DB_URL"):
            _resolve_database_url()

    def test_levanta_runtime_error_quando_env_vazia(self, monkeypatch):
        monkeypatch.setenv("MARKET_DB_URL", "")
        with pytest.raises(RuntimeError, match="MARKET_DB_URL"):
            _resolve_database_url()

    def test_mensagem_de_erro_orienta_o_usuario(self, monkeypatch):
        monkeypatch.delenv("MARKET_DB_URL", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            _resolve_database_url()
        msg = str(exc_info.value)
        assert "sqlite" in msg.lower()
        assert "postgresql" in msg.lower()
        assert ".env" in msg

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
