"""
tests/test_credentials.py
Cobre `backend.config.credentials` (ISSUE-026):
  - parse leniente do CSV
  - construção de URL a partir do dict
  - precedência env > CSV > erro
  - localização da pasta `Documents/`
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from backend.config import credentials as cred


# ─── Parsing ──────────────────────────────────────────────────────────────


class TestParseCredCsv:
    def test_separador_ponto_virgula(self):
        text = "key;value\nuser;postgres\npassword;abc123\n"
        result = cred._parse_cred_csv(text)
        assert result == {"user": "postgres", "password": "abc123"}

    def test_separador_dois_pontos(self):
        text = "user:postgres\nbanco:energia\n"
        result = cred._parse_cred_csv(text)
        assert result == {"user": "postgres", "banco": "energia"}

    def test_mistura_separadores_no_mesmo_arquivo(self):
        # Caso real do CSV do Lucas: linhas 1-5 com `;`, linha 6 com `:`.
        text = dedent(
            """\
            key;value
            user;postgres
            password;141592
            host;localhost
            port;5432
            banco:energia
            """
        )
        result = cred._parse_cred_csv(text)
        assert result == {
            "user": "postgres",
            "password": "141592",
            "host": "localhost",
            "port": "5432",
            "banco": "energia",
        }

    def test_ignora_cabecalho_key_value(self):
        text = "key;value\nuser;x\n"
        assert "key" not in cred._parse_cred_csv(text)

    def test_ignora_linhas_em_branco(self):
        text = "\n\nuser;x\n\n"
        assert cred._parse_cred_csv(text) == {"user": "x"}

    def test_ignora_linhas_malformadas(self):
        text = "user;x\nlinha-sem-separador\n;\nfoo;\n"
        # `;` (key vazia) e `foo;` (value vazio) caem fora.
        assert cred._parse_cred_csv(text) == {"user": "x"}

    def test_chaves_lowercased(self):
        text = "USER;postgres\nPassWord;abc\n"
        assert cred._parse_cred_csv(text) == {"user": "postgres", "password": "abc"}

    def test_tolera_bom(self):
        text = "﻿user;postgres\n"
        assert cred._parse_cred_csv(text) == {"user": "postgres"}

    def test_strip_em_chaves_e_valores(self):
        text = "  user ;  postgres  \n"
        assert cred._parse_cred_csv(text) == {"user": "postgres"}


# ─── Construção da URL ───────────────────────────────────────────────────


class TestBuildUrlFromCreds:
    def test_url_completa(self):
        creds = {
            "user": "postgres",
            "password": "abc",
            "host": "localhost",
            "port": "5432",
            "banco": "energia",
        }
        assert (
            cred._build_url_from_creds(creds)
            == "postgresql+psycopg2://postgres:abc@localhost:5432/energia"
        )

    def test_aceita_username_em_vez_de_user(self):
        creds = {
            "username": "u",
            "password": "p",
            "host": "h",
            "port": "1",
            "banco": "b",
        }
        assert cred._build_url_from_creds(creds) is not None

    def test_aceita_database_em_vez_de_banco(self):
        creds = {
            "user": "u",
            "password": "p",
            "host": "h",
            "port": "1",
            "database": "b",
        }
        assert cred._build_url_from_creds(creds) is not None

    def test_aceita_db_em_vez_de_banco(self):
        creds = {"user": "u", "password": "p", "host": "h", "port": "1", "db": "b"}
        assert cred._build_url_from_creds(creds) is not None

    def test_aceita_senha_em_vez_de_password(self):
        creds = {
            "user": "u",
            "senha": "p",
            "host": "h",
            "port": "1",
            "banco": "b",
        }
        assert cred._build_url_from_creds(creds) is not None

    def test_retorna_none_quando_falta_chave_obrigatoria(self):
        creds = {"user": "u", "password": "p", "host": "h"}  # sem port/banco
        assert cred._build_url_from_creds(creds) is None


# ─── Resolução end-to-end ────────────────────────────────────────────────


class TestResolveDatabaseUrl:
    def test_env_var_tem_precedencia(self, monkeypatch):
        monkeypatch.setenv("MARKET_DB_URL", "sqlite:///./qualquer.db")
        # Mesmo se o CSV existisse, env vence.
        monkeypatch.setattr(cred, "_read_cred_file", lambda: "postgresql://x")
        assert cred.resolve_database_url() == "sqlite:///./qualquer.db"

    def test_csv_quando_env_ausente(self, monkeypatch):
        monkeypatch.delenv("MARKET_DB_URL", raising=False)
        monkeypatch.setattr(
            cred, "_read_cred_file", lambda: "postgresql+psycopg2://u:p@h:1/b"
        )
        assert cred.resolve_database_url() == "postgresql+psycopg2://u:p@h:1/b"

    def test_csv_quando_env_vazia(self, monkeypatch):
        monkeypatch.setenv("MARKET_DB_URL", "")
        monkeypatch.setattr(
            cred, "_read_cred_file", lambda: "postgresql+psycopg2://u:p@h:1/b"
        )
        assert cred.resolve_database_url() == "postgresql+psycopg2://u:p@h:1/b"

    def test_erro_quando_env_e_csv_ausentes(self, monkeypatch):
        monkeypatch.delenv("MARKET_DB_URL", raising=False)
        monkeypatch.setattr(cred, "_read_cred_file", lambda: None)
        with pytest.raises(RuntimeError) as exc:
            cred.resolve_database_url()
        msg = str(exc.value)
        assert "MARKET_DB_URL" in msg
        assert "Cred/8.CREDENCIAIS/2.DB/credenciais.csv" in msg

    def test_erro_quando_csv_existe_mas_e_invalido(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MARKET_DB_URL", raising=False)
        # Simula docs dir + CSV com chaves faltando.
        docs = tmp_path / "Documents"
        cred_dir = docs / cred.CRED_DB_RELPATH.parent
        cred_dir.mkdir(parents=True)
        (docs / cred.CRED_DB_RELPATH).write_text("user;u\n", encoding="utf-8")
        monkeypatch.setattr(cred, "_find_documents_dir", lambda *_: docs)
        with pytest.raises(RuntimeError, match="chaves obrigatórias"):
            cred.resolve_database_url()


class TestFindDocumentsDir:
    def test_acha_documents_no_ancestral(self, tmp_path):
        docs = tmp_path / "Documents"
        nested = docs / "a" / "b" / "c"
        nested.mkdir(parents=True)
        assert cred._find_documents_dir(nested) == docs

    def test_case_insensitive(self, tmp_path):
        docs = tmp_path / "DOCUMENTS"
        nested = docs / "x"
        nested.mkdir(parents=True)
        assert cred._find_documents_dir(nested) == docs

    def test_retorna_none_quando_nao_ha_documents_no_path(self, tmp_path):
        nested = tmp_path / "outra-pasta" / "x"
        nested.mkdir(parents=True)
        assert cred._find_documents_dir(nested) is None


class TestReadCredFile:
    def test_le_csv_real(self, monkeypatch, tmp_path):
        docs = tmp_path / "Documents"
        cred_dir = docs / cred.CRED_DB_RELPATH.parent
        cred_dir.mkdir(parents=True)
        (docs / cred.CRED_DB_RELPATH).write_text(
            dedent(
                """\
                key;value
                user;postgres
                password;abc
                host;localhost
                port;5432
                banco:energia
                """
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(cred, "_find_documents_dir", lambda *_: docs)
        url = cred._read_cred_file()
        assert url == "postgresql+psycopg2://postgres:abc@localhost:5432/energia"

    def test_retorna_none_se_arquivo_nao_existe(self, monkeypatch, tmp_path):
        docs = tmp_path / "Documents"
        docs.mkdir()
        monkeypatch.setattr(cred, "_find_documents_dir", lambda *_: docs)
        assert cred._read_cred_file() is None

    def test_retorna_none_se_documents_nao_existe(self, monkeypatch):
        monkeypatch.setattr(cred, "_find_documents_dir", lambda *_: None)
        assert cred._read_cred_file() is None
