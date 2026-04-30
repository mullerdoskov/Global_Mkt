"""
api/assets.py
Endpoints de ativos e busca.
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.db.connection import get_session
from backend.db.schema import Asset, Company, Country, SectorGICS, PriceDaily
from backend.api.models import AssetInfo, AssetDetail, AssetListResponse, CompanyInfo
from backend.api._limiter import limiter

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetListResponse)
@limiter.limit(settings.rate_limit_default)
def list_assets(
    request: Request,
    asset_type: Optional[str] = Query(None, description="Tipo de ativo: stock, index, commodity, fx, crypto"),
    country: Optional[str] = Query(None, description="Código ISO-2 do país"),
    sector: Optional[str] = Query(None, description="Setor GICS"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamanho da página"),
) -> AssetListResponse:
    """
    Lista ativos com filtros opcionais e paginação.

    Parâmetros:
    - asset_type: Filtra por tipo (stock, index, commodity, fx, crypto)
    - country: Filtra por país (ISO-2, ex: BR, US)
    - sector: Filtra por setor GICS
    - page: Número da página (default: 1)
    - page_size: Itens por página (default: 20, máx: 100)
    """
    session = get_session()
    try:
        query = select(Asset)

        # Filtro por tipo
        if asset_type:
            query = query.where(Asset.asset_type == asset_type)

        # Filtro por país (via Company)
        if country:
            query = query.join(Company, Company.id == Asset.company_id)
            query = query.join(Country, Country.id == Company.country_id)
            query = query.where(Country.iso2 == country)

        # Filtro por setor (via Company)
        if sector:
            if not query._where_criterions:  # Se ainda não fez join com Company
                query = query.join(Company, Company.id == Asset.company_id)
            query = query.join(SectorGICS, SectorGICS.id == Company.sector_gics_id)
            query = query.where(SectorGICS.sector == sector)

        # Contar total
        total_query = select(func.count()).select_from(query.alias())
        total = session.execute(total_query).scalar() or 0

        # Paginação
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        assets = session.execute(query).scalars().all()

        asset_infos = [
            AssetInfo(
                symbol=a.symbol,
                name=a.name or a.symbol,
                asset_type=a.asset_type.value,
                currency=a.currency,
                exchange=a.exchange,
                is_active=a.is_active,
            )
            for a in assets
        ]

        return AssetListResponse(
            total=total,
            page=page,
            page_size=page_size,
            assets=asset_infos,
        )
    finally:
        session.close()


@router.get("/search", response_model=AssetListResponse)
@limiter.limit(settings.rate_limit_default)
def search_assets(
    request: Request,
    q: str = Query(..., min_length=1, max_length=50, description="Termo de busca por símbolo ou nome"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> AssetListResponse:
    """
    Busca ativos por símbolo ou nome.

    Parâmetro:
    - q: Termo de busca (símbolos ou nomes contendo este texto)
    """
    session = get_session()
    try:
        search_term = f"%{q.upper()}%"

        # Busca por símbolo ou nome (case-insensitive)
        query = select(Asset).where(
            (Asset.symbol.ilike(search_term)) | (Asset.name.ilike(search_term))
        )

        # Contar total
        total_query = select(func.count()).select_from(query.alias())
        total = session.execute(total_query).scalar() or 0

        # Paginação
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        assets = session.execute(query).scalars().all()

        asset_infos = [
            AssetInfo(
                symbol=a.symbol,
                name=a.name or a.symbol,
                asset_type=a.asset_type.value,
                currency=a.currency,
                exchange=a.exchange,
                is_active=a.is_active,
            )
            for a in assets
        ]

        return AssetListResponse(
            total=total,
            page=page,
            page_size=page_size,
            assets=asset_infos,
        )
    finally:
        session.close()


@router.get("/{symbol}", response_model=AssetDetail)
@limiter.limit(settings.rate_limit_default)
def get_asset_detail(request: Request, symbol: str) -> AssetDetail:
    """
    Retorna detalhes completos de um ativo.

    Inclui informações da companhia (se for ação) e último preço.
    """
    session = get_session()
    try:
        # Busca o ativo
        asset = session.execute(
            select(Asset).where(Asset.symbol == symbol)
        ).scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found")

        # Busca companhia associada
        company_info = None
        if asset.company_id:
            company = session.execute(
                select(Company).where(Company.id == asset.company_id)
            ).scalar_one_or_none()

            if company:
                # Busca país e setor
                country = None
                sector = None
                if company.country_id:
                    country = session.execute(
                        select(Country).where(Country.id == company.country_id)
                    ).scalar_one_or_none()
                if company.sector_gics_id:
                    sector = session.execute(
                        select(SectorGICS).where(SectorGICS.id == company.sector_gics_id)
                    ).scalar_one_or_none()

                company_info = CompanyInfo(
                    ticker=company.ticker,
                    name=company.name,
                    country_iso2=country.iso2 if country else None,
                    sector=sector.sector if sector else None,
                    market_cap=company.market_cap,
                    employees=company.employees,
                    currency=company.currency,
                    exchange=company.exchange,
                )

        # Busca último preço
        latest_price_query = select(PriceDaily).where(
            PriceDaily.asset_id == asset.id
        ).order_by(PriceDaily.date.desc()).limit(1)

        latest_price_row = session.execute(latest_price_query).scalar_one_or_none()
        latest_price = float(latest_price_row.close) if latest_price_row and latest_price_row.close else None
        latest_date = latest_price_row.date if latest_price_row else None

        return AssetDetail(
            symbol=asset.symbol,
            name=asset.name or asset.symbol,
            asset_type=asset.asset_type.value,
            currency=asset.currency,
            exchange=asset.exchange,
            company=company_info,
            latest_price=latest_price,
            latest_date=latest_date,
        )

    finally:
        session.close()
