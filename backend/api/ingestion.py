"""
api/ingestion.py
Endpoints de status de ingestão.
"""

from datetime import datetime
from fastapi import APIRouter, Request
from sqlalchemy import select, desc

from backend.config.settings import settings
from backend.db.connection import get_session
from backend.db.schema import IngestionLog
from backend.api.models import IngestionStatusResponse, IngestionLogEntry
from backend.api._limiter import limiter

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get("/status", response_model=IngestionStatusResponse)
@limiter.limit(settings.rate_limit_default)
def get_ingestion_status(request: Request) -> IngestionStatusResponse:
    """
    Retorna status geral da ingestão com log resumido dos últimos registros.

    Inclui:
    - Contagem de assets ingeridos
    - Contagem de sucesso/erro
    - Últimas 10 entradas de log
    """
    session = get_session()
    try:
        # Busca últimos 10 logs
        logs_query = select(IngestionLog).order_by(desc(IngestionLog.started_at)).limit(10)
        logs = session.execute(logs_query).scalars().all()

        # Conta sucesso e erros
        success_count = 0
        error_count = 0
        for log in logs:
            if log.status.value == "success":
                success_count += 1
            elif log.status.value == "error":
                error_count += 1

        # Converte para modelo
        log_entries = [
            IngestionLogEntry(
                symbol=log.symbol,
                ingestion_type=log.ingestion_type,
                status=log.status.value,
                rows_inserted=log.rows_inserted,
                started_at=log.started_at,
                finished_at=log.finished_at,
                duration_seconds=log.duration_seconds,
                error_message=log.error_message,
            )
            for log in logs
        ]

        return IngestionStatusResponse(
            last_update=logs[0].started_at if logs else None,
            total_assets=len(set(log.symbol for log in logs)),
            recent_logs=log_entries,
            success_count=success_count,
            error_count=error_count,
        )

    finally:
        session.close()
