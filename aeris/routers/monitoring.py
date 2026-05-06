from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session
from aeris.routers.auth import get_current_user, TokenData
from aeris.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


async def get_monitoring_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MonitoringService:
    return MonitoringService(session)


@router.get("/dashboard")
async def get_dashboard(
    days: int = Query(default=7, ge=1, le=30),
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    service: Annotated[MonitoringService, Depends(get_monitoring_service)] = None,
):
    """Get dashboard statistics."""
    return await service.get_dashboard_stats(days)


@router.get("/traces")
async def get_traces(
    conversation_id: Optional[int] = None,
    provider: Optional[str] = None,
    error_only: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    service: Annotated[MonitoringService, Depends(get_monitoring_service)] = None,
):
    """Get LLM traces."""
    traces = await service.get_traces(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
        provider=provider,
        error_only=error_only,
        skip=skip,
        limit=limit,
    )
    return traces


@router.get("/traces/{trace_id}")
async def get_trace_detail(
    trace_id: str,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    service: Annotated[MonitoringService, Depends(get_monitoring_service)] = None,
):
    """Get trace detail."""
    trace = await service.get_trace_detail(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.get("/model-usage")
async def get_model_usage(
    days: int = Query(default=7, ge=1, le=30),
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    service: Annotated[MonitoringService, Depends(get_monitoring_service)] = None,
):
    """Get model usage statistics."""
    return await service.get_model_usage(days)


@router.get("/daily-stats")
async def get_daily_stats(
    days: int = Query(default=7, ge=1, le=30),
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    service: Annotated[MonitoringService, Depends(get_monitoring_service)] = None,
):
    """Get daily token usage and latency distribution."""
    return await service.get_daily_stats(days)
