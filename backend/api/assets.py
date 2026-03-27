"""
Endpoints: /api/assets, /api/assets/search, /api/assets/{symbol}
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.models import AssetDetail, AssetItem, AssetListResponse
from backend.db.connection import get_db
from backend.db.schema import Asset, PriceDaily

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=AssetListResponse)
def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    asset_type: str | None = Query(None, description="stock, index, commodity, fx, crypto, etf"),
    country: str | None = Query(None, description="BR, US, etc"),
    db: Session = Depends(get_db),
):
    """Lista assets com paginação e filtros opcionais."""
    query = select(Asset).where(Asset.is_active == True)

    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
    if country:
        query = query.where(Asset.country == country.upper())

    # Total
    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    # Paginação
    offset = (page - 1) * page_size
    query = query.order_by(Asset.symbol).offset(offset).limit(page_size)
    assets = db.execute(query).scalars().all()

    return AssetListResponse(
        total=total,
        page=page,
        page_size=page_size,
        assets=[
            AssetItem(
                id=a.id,
                symbol=a.symbol,
                name=a.name,
                asset_type=a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type),
                country=a.country,
                is_active=a.is_active,
            )
            for a in assets
        ],
    )


@router.get("/search", response_model=AssetListResponse)
def search_assets(
    q: str = Query(..., min_length=1, description="Busca por símbolo ou nome"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Busca assets por símbolo ou nome (case-insensitive)."""
    pattern = f"%{q}%"
    query = (
        select(Asset)
        .where(
            Asset.is_active == True,
            (Asset.symbol.ilike(pattern) | Asset.name.ilike(pattern)),
        )
        .order_by(Asset.symbol)
        .limit(limit)
    )

    assets = db.execute(query).scalars().all()

    return AssetListResponse(
        total=len(assets),
        page=1,
        page_size=limit,
        assets=[
            AssetItem(
                id=a.id,
                symbol=a.symbol,
                name=a.name,
                asset_type=a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type),
                country=a.country,
                is_active=a.is_active,
            )
            for a in assets
        ],
    )


@router.get("/{symbol}", response_model=AssetDetail)
def get_asset(symbol: str, db: Session = Depends(get_db)):
    """Detalhe de um asset específico, incluindo último preço."""
    asset = db.execute(
        select(Asset).where(Asset.symbol == symbol.upper())
    ).scalar_one_or_none()

    if not asset:
        # Tentar sem upper (tickers com sufixo tipo .SA)
        asset = db.execute(
            select(Asset).where(Asset.symbol == symbol)
        ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' não encontrado")

    # Último preço
    latest_price = None
    price = db.execute(
        select(PriceDaily)
        .where(PriceDaily.asset_id == asset.id)
        .order_by(PriceDaily.date.desc())
        .limit(1)
    ).scalar_one_or_none()

    if price:
        latest_price = {
            "date": str(price.date),
            "close": price.close,
            "change_pct": price.change_pct,
            "volume": price.volume,
            "open": price.open,
            "high": price.high,
            "low": price.low,
        }

    return AssetDetail(
        id=asset.id,
        symbol=asset.symbol,
        name=asset.name,
        asset_type=asset.asset_type.value if hasattr(asset.asset_type, "value") else str(asset.asset_type),
        country=asset.country,
        is_active=asset.is_active,
        latest_price=latest_price,
        created_at=asset.created_at,
    )
