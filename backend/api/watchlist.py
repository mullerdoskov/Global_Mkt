"""
api/watchlist.py — ISSUE-018

Watchlist persistente atrelada a sessão anônima via cookie UUID.
Ver ADR de 2026-04-30 em DECISIONS.md.

Endpoints:
- GET    /api/watchlist                  → lista items da sessão (200)
- POST   /api/watchlist/{symbol}         → adiciona ou marca presente (200/201)
- DELETE /api/watchlist/{symbol}         → remove ou no-op (204)

Idempotência:
- POST de símbolo já presente → 200, mesma posição.
- DELETE de símbolo ausente da watchlist → 204.
- 404 só dispara se `symbol` não existe na tabela `assets` —
  diferenciar "asset desconhecido" de "asset não está na watchlist".

Cookie/sessão: gerenciados pela dependency `ensure_session` em
`backend/api/_session.py`. Endpoints que usam `Depends(ensure_session)`
recebem o UUID da sessão e — se for primeira request — o cookie é
setado na response automaticamente.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError

from backend.api._limiter import limiter
from backend.api._session import ensure_session
from backend.api.models import (
    WatchlistItemOut,
    WatchlistResponse,
    WatchlistMutationResponse,
)
from backend.config.settings import settings
from backend.db.connection import get_session
from backend.db.schema import Asset, WatchlistItem

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
logger = logging.getLogger("market_platform")


def _serialize_item(item: WatchlistItem, asset: Asset) -> WatchlistItemOut:
    return WatchlistItemOut(
        symbol=asset.symbol,
        name=asset.name or asset.symbol,
        asset_type=asset.asset_type.value,
        currency=asset.currency,
        exchange=asset.exchange,
        position=item.position,
        added_at=item.added_at,
    )


@router.get("", response_model=WatchlistResponse)
@limiter.limit(settings.rate_limit_watchlist_read)
def get_watchlist(
    request: Request,
    response: Response,
    session_uuid: uuid.UUID = Depends(ensure_session),
) -> WatchlistResponse:
    """Lista os items da watchlist da sessão atual, ordem por position ASC.

    Sessão nova (sem items) → 200 com lista vazia. Nunca 404.
    """
    db = get_session()
    try:
        rows = db.execute(
            select(WatchlistItem, Asset)
            .join(Asset, Asset.id == WatchlistItem.asset_id)
            .where(WatchlistItem.session_uuid == session_uuid)
            .order_by(WatchlistItem.position.asc(), WatchlistItem.added_at.asc())
        ).all()

        items = [_serialize_item(item, asset) for item, asset in rows]
        return WatchlistResponse(items=items)
    finally:
        db.close()


@router.post(
    "/{symbol}",
    response_model=WatchlistMutationResponse,
    status_code=200,
)
@limiter.limit(settings.rate_limit_watchlist_write)
def add_to_watchlist(
    request: Request,
    response: Response,
    symbol: str,
    session_uuid: uuid.UUID = Depends(ensure_session),
) -> WatchlistMutationResponse:
    """Adiciona `symbol` à watchlist da sessão.

    Idempotente: se já está na watchlist, retorna 200 com a mesma position.
    `position` default = max(position) + 1 da sessão (fim da lista).

    404 se `symbol` não existe na tabela `assets`.
    """
    db = get_session()
    try:
        asset = db.execute(
            select(Asset).where(Asset.symbol == symbol)
        ).scalar_one_or_none()
        if asset is None:
            raise HTTPException(
                status_code=404,
                detail=f"Asset '{symbol}' not found",
            )

        existing = db.execute(
            select(WatchlistItem).where(
                (WatchlistItem.session_uuid == session_uuid)
                & (WatchlistItem.asset_id == asset.id)
            )
        ).scalar_one_or_none()

        if existing is not None:
            return WatchlistMutationResponse(
                symbol=asset.symbol,
                in_watchlist=True,
                position=existing.position,
            )

        next_position = db.execute(
            select(func.coalesce(func.max(WatchlistItem.position), -1) + 1)
            .where(WatchlistItem.session_uuid == session_uuid)
        ).scalar_one()

        new_item = WatchlistItem(
            session_uuid=session_uuid,
            asset_id=asset.id,
            position=int(next_position),
        )
        db.add(new_item)
        try:
            db.commit()
        except IntegrityError:
            # Race condition pouco provável (mesmo cookie + 2 POSTs em paralelo);
            # `UNIQUE(session_uuid, asset_id)` defende. Fallback: re-ler.
            db.rollback()
            existing = db.execute(
                select(WatchlistItem).where(
                    (WatchlistItem.session_uuid == session_uuid)
                    & (WatchlistItem.asset_id == asset.id)
                )
            ).scalar_one()
            return WatchlistMutationResponse(
                symbol=asset.symbol,
                in_watchlist=True,
                position=existing.position,
            )

        db.refresh(new_item)
        return WatchlistMutationResponse(
            symbol=asset.symbol,
            in_watchlist=True,
            position=new_item.position,
        )
    finally:
        db.close()


@router.delete("/{symbol}", status_code=204)
@limiter.limit(settings.rate_limit_watchlist_write)
def remove_from_watchlist(
    request: Request,
    response: Response,
    symbol: str,
    session_uuid: uuid.UUID = Depends(ensure_session),
) -> Response:
    """Remove `symbol` da watchlist da sessão.

    Idempotente: 204 mesmo se o item não estava na watchlist.
    404 SÓ se `symbol` não existe na tabela `assets` — diferencia
    "asset desconhecido" (input inválido) de "asset não estava na
    watchlist" (estado terminal já correto).
    """
    db = get_session()
    try:
        asset = db.execute(
            select(Asset).where(Asset.symbol == symbol)
        ).scalar_one_or_none()
        if asset is None:
            raise HTTPException(
                status_code=404,
                detail=f"Asset '{symbol}' not found",
            )

        db.execute(
            delete(WatchlistItem).where(
                (WatchlistItem.session_uuid == session_uuid)
                & (WatchlistItem.asset_id == asset.id)
            )
        )
        db.commit()
        return Response(status_code=204)
    finally:
        db.close()
