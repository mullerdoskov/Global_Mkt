"""
Endpoint: /api/ingestion/status
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.models import IngestionLogItem, IngestionStatusResponse
from backend.db.connection import get_db
from backend.db.schema import Asset, IngestionLog, IngestionStatus

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.get("/status", response_model=IngestionStatusResponse)
def ingestion_status(db: Session = Depends(get_db)):
    """Status geral da ingestão: contagens e logs recentes."""
    total_assets = db.execute(select(func.count(Asset.id))).scalar() or 0

    success_count = db.execute(
        select(func.count(IngestionLog.id)).where(IngestionLog.status == IngestionStatus.success)
    ).scalar() or 0

    error_count = db.execute(
        select(func.count(IngestionLog.id)).where(IngestionLog.status == IngestionStatus.error)
    ).scalar() or 0

    partial_count = db.execute(
        select(func.count(IngestionLog.id)).where(IngestionLog.status == IngestionStatus.partial)
    ).scalar() or 0

    # Logs mais recentes
    recent = db.execute(
        select(IngestionLog, Asset.symbol)
        .join(Asset, Asset.id == IngestionLog.asset_id)
        .order_by(IngestionLog.started_at.desc())
        .limit(20)
    ).fetchall()

    recent_logs = [
        IngestionLogItem(
            symbol=row[1],
            status=row[0].status.value if hasattr(row[0].status, "value") else str(row[0].status),
            data_type=row[0].data_type or "prices",
            rows_inserted=row[0].rows_inserted or 0,
            rows_updated=row[0].rows_updated or 0,
            started_at=row[0].started_at,
            finished_at=row[0].finished_at,
            error_message=row[0].error_message,
        )
        for row in recent
    ]

    return IngestionStatusResponse(
        total_assets=total_assets,
        success_count=success_count,
        error_count=error_count,
        partial_count=partial_count,
        recent_logs=recent_logs,
    )
