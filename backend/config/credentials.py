"""
backend/config/credentials.py
Resolução de credenciais sensíveis a partir de fontes externas ao repo.

Motivação (ISSUE-026): a senha do banco não pode viver no `.env` do repo
nem em variáveis hardcoded. Lucas mantém suas credenciais em
`~/Documents/Cred/8.CREDENCIAIS/<categoria>/credenciais.csv` (fora de
qualquer árvore versionada). Este módulo faz o backend (e o `alembic/env.py`)
ler dessa pasta sem qualquer credencial no código ou em `.env`.

Ordem de resolução de `MARKET_DB_URL`:
1. Variável de ambiente `MARKET_DB_URL` (override explícito — mantém o
   contrato desde ISSUE-004 para CI/testes/Docker).
2. Arquivo CSV em `<Documents>/Cred/8.CREDENCIAIS/2.DB/credenciais.csv`,
   localizado subindo a partir da raiz do projeto até encontrar uma
   pasta chamada `Documents` (case-insensitive).
3. `RuntimeError` com mensagem orientativa.

O parser do CSV é tolerante: aceita separador `;` ou `:`, ignora BOM e
linha de cabeçalho `key;value`, e aceita as variantes (`user`/`username`,
`password`/`senha`, `port`/`porta`, `banco`/`database`/`db`).

Importar este módulo é no-op (consistente com ISSUE-014): nenhum I/O em
escopo de import. `resolve_database_url()` é uma função pura — chamadas
repetidas refazem a leitura do env / filesystem. O caching real fica em
`backend.db.connection.get_engine()` (lru_cache do engine), não aqui.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional


CRED_DB_RELPATH = Path("Cred") / "8.CREDENCIAIS" / "2.DB" / "credenciais.csv"


def _project_root() -> Path:
    """Raiz do projeto: `<repo>/market_platform_unified/`.

    `<repo>/market_platform_unified/backend/config/credentials.py`
    → `parents[2]` = `<repo>/market_platform_unified/`.
    """
    return Path(__file__).resolve().parents[2]


def _find_documents_dir(start: Optional[Path] = None) -> Optional[Path]:
    """Sobe a partir de `start` (default: raiz do projeto) até encontrar
    uma pasta `Documents` (case-insensitive). Retorna None se não estiver
    dentro de uma árvore com `Documents/` em algum ancestral.
    """
    cur = (start or _project_root()).resolve()
    for parent in [cur, *cur.parents]:
        if parent.name.lower() == "documents":
            return parent
    return None


def _parse_cred_csv(text: str) -> dict[str, str]:
    """Parse leniente: aceita `key;value` ou `key:value` por linha.

    - Tolera BOM no início do arquivo.
    - Ignora cabeçalho `key;value` / `key:value`.
    - Ignora linhas em branco e linhas malformadas.
    - Lowercase nas chaves.
    """
    result: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip().lstrip("﻿")
        if not line:
            continue
        low = line.lower()
        if low.startswith("key;value") or low.startswith("key:value"):
            continue
        parts = re.split(r"[;:]", line, maxsplit=1)
        if len(parts) != 2:
            continue
        key = parts[0].strip().lower()
        value = parts[1].strip()
        if key and value:
            result[key] = value
    return result


def _build_url_from_creds(creds: dict[str, str]) -> Optional[str]:
    """Constrói URL `postgresql+psycopg2://` a partir do dict parseado.

    Aceita variantes de nome (user/username, password/senha, port/porta,
    banco/database/db). Retorna None se faltar qualquer chave obrigatória.
    """
    user = creds.get("user") or creds.get("username")
    password = creds.get("password") or creds.get("senha")
    host = creds.get("host")
    port = creds.get("port") or creds.get("porta")
    banco = creds.get("banco") or creds.get("database") or creds.get("db")
    if not all([user, password, host, port, banco]):
        return None
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{banco}"


def _read_cred_file() -> Optional[str]:
    """Tenta ler o CSV de credenciais e retornar a URL pronta. None se o
    arquivo não existe ou se o conteúdo é insuficiente.
    """
    docs = _find_documents_dir()
    if docs is None:
        return None
    cred_path = docs / CRED_DB_RELPATH
    if not cred_path.is_file():
        return None
    text = cred_path.read_text(encoding="utf-8")
    creds = _parse_cred_csv(text)
    url = _build_url_from_creds(creds)
    if url is None:
        raise RuntimeError(
            f"Arquivo de credenciais encontrado em {cred_path} mas faltam "
            "chaves obrigatórias. Esperado: user, password, host, port, banco. "
            f"Chaves presentes: {sorted(creds.keys())}."
        )
    return url


def resolve_database_url() -> str:
    """Resolve `MARKET_DB_URL`. Ordem: env → CSV externo → erro.

    Sem cache — cada chamada refaz a resolução. Cache de engine fica em
    `backend.db.connection.get_engine()`.
    """
    env_url = os.getenv("MARKET_DB_URL")
    if env_url:
        return env_url

    csv_url = _read_cred_file()
    if csv_url:
        return csv_url

    raise RuntimeError(
        "MARKET_DB_URL não está definida e o arquivo de credenciais externo "
        f"não foi encontrado em <Documents>/{CRED_DB_RELPATH.as_posix()}. "
        "Configure uma das duas opções:\n"
        "  - export MARKET_DB_URL=postgresql+psycopg2://USER:PASS@host:5432/db\n"
        "  - export MARKET_DB_URL=sqlite:///market_db.sqlite (dev)\n"
        "  - ou crie o CSV de credenciais com user/password/host/port/banco."
    )
