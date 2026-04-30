"""
api/_session.py — ISSUE-018

Identidade anônima do usuário via cookie UUID. Ver ADR de 2026-04-30 em
`DECISIONS.md`. Sem PII no banco; o cookie é só uma chave opaca de sessão.

Uso típico em handler:

    @router.get("/something")
    def handler(
        request: Request,
        response: Response,
        session_uuid: uuid.UUID = Depends(ensure_session),
    ):
        ...

`ensure_session(request, response)` — dependency FastAPI:
1. Lê o cookie `settings.session_cookie_name` da request.
2. Se ausente ou inválido (UUID malformado), gera novo UUID v4, insere
   linha em `user_sessions` e seta o cookie no `response`.
3. Se válido mas não estiver na tabela, idem (caso de cookie órfão de
   uma instância anterior do banco).
4. Se válido e existente, atualiza `last_seen_at`.

A dependency abre e fecha sua própria sessão SQL. Endpoints que já
abrem sessão (a maioria) lidam normalmente — não há conflito de
transação porque a `ensure_session` faz commit antes do handler rodar.

Cookie config (ver settings):
- `HttpOnly=True` (impede leitura via JS)
- `Secure` configurável (default True; ajustar para False em dev http)
- `SameSite=Lax` (envia em navegação top-level mas bloqueia POST cross-site)
- `Path=/`, sem `Domain` (default = origem da request)
- `Max-Age` ~10 anos
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import Request, Response
from sqlalchemy import select

from backend.config.settings import settings
from backend.db.connection import get_session
from backend.db.schema import UserSession

logger = logging.getLogger("market_platform")


def _parse_uuid(raw: Optional[str]) -> Optional[uuid.UUID]:
    """Parse defensivo de UUID. Retorna None se vazio ou malformado."""
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except (ValueError, TypeError):
        return None


def _set_session_cookie(response: Response, session_uuid: uuid.UUID) -> None:
    """Seta o cookie de sessão na response com a config das settings."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=str(session_uuid),
        max_age=settings.session_cookie_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def ensure_session(request: Request, response: Response) -> uuid.UUID:
    """Garante que a request tem uma sessão válida em `user_sessions`.

    Dependency FastAPI: usar via `Depends(ensure_session)`. Retorna o
    UUID da sessão (já existente ou recém-criada).
    """
    raw_cookie = request.cookies.get(settings.session_cookie_name)
    cookie_uuid = _parse_uuid(raw_cookie)

    db = get_session()
    try:
        session_row: Optional[UserSession] = None
        if cookie_uuid is not None:
            session_row = db.execute(
                select(UserSession).where(UserSession.uuid == cookie_uuid)
            ).scalar_one_or_none()

        if session_row is None:
            # Cookie ausente, malformado ou referencia sessão inexistente.
            # Em qualquer dos casos, gerar nova session.
            new_uuid = uuid.uuid4()
            session_row = UserSession(uuid=new_uuid)
            db.add(session_row)
            db.commit()
            _set_session_cookie(response, new_uuid)
            logger.debug("ensure_session: nova sessão %s", new_uuid)
            return new_uuid

        # Sessão existente — atualizar last_seen_at.
        from sqlalchemy import update, func
        db.execute(
            update(UserSession)
            .where(UserSession.uuid == session_row.uuid)
            .values(last_seen_at=func.now())
        )
        db.commit()
        return session_row.uuid
    finally:
        db.close()
