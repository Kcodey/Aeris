"""Skill usage monitoring routes."""

from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlmodel import select

from aeris.database import get_session
from aeris.routers.auth import get_current_user, TokenData
from aeris.models.skill_usage import SkillUsage

router = APIRouter(prefix="/monitoring", tags=["skill-usage"])


@router.get("/skill-usage/stats")
async def get_skill_usage_stats(
    hours: int = Query(default=168, ge=1, le=720),
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
):
    """Get skill usage statistics. Admin sees all, regular user sees own."""
    from datetime import timedelta

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Total calls by skill
    stmt = (
        select(
            SkillUsage.skill_name,
            func.count(SkillUsage.id).label("call_count"),
        )
        .where(SkillUsage.timestamp >= cutoff_time)
    )
    if not current_user.is_admin:
        stmt = stmt.where(SkillUsage.user_id == current_user.user_id)
    stmt = stmt.group_by(SkillUsage.skill_name).order_by(desc("call_count"))

    result = await session.execute(stmt)
    rows = result.all()

    stats = []
    for row in rows:
        stats.append({
            "skill_name": row.skill_name,
            "call_count": row.call_count,
        })

    return {
        "period_hours": hours,
        "stats": stats,
    }


@router.get("/skill-usage/timeline")
async def get_skill_usage_timeline(
    skill_name: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=720),
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
):
    """Get skill usage timeline. Admin sees all, regular user sees own."""
    from datetime import timedelta

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    stmt = (
        select(
            func.date_trunc('hour', SkillUsage.timestamp).label("hour"),
            func.count(SkillUsage.id).label("count"),
        )
        .where(SkillUsage.timestamp >= cutoff_time)
    )
    if not current_user.is_admin:
        stmt = stmt.where(SkillUsage.user_id == current_user.user_id)

    if skill_name:
        stmt = stmt.where(SkillUsage.skill_name == skill_name)

    stmt = stmt.group_by("hour").order_by("hour")

    result = await session.execute(stmt)
    rows = result.all()

    return {
        "skill_name": skill_name,
        "period_hours": hours,
        "timeline": [
            {"hour": row.hour.isoformat() if row.hour else None, "count": row.count}
            for row in rows
        ],
    }


@router.get("/skill-usage/recent")
async def get_recent_skill_usage(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
):
    """Get recent skill usage records. Admin sees all, regular user sees own."""
    stmt = select(SkillUsage)
    if not current_user.is_admin:
        stmt = stmt.where(SkillUsage.user_id == current_user.user_id)
    stmt = stmt.order_by(desc(SkillUsage.timestamp)).limit(limit)

    result = await session.execute(stmt)
    usages = result.scalars().all()

    return [
        {
            "id": u.id,
            "skill_name": u.skill_name,
            "success": u.success,
            "latency_ms": u.latency_ms,
            "timestamp": u.timestamp.isoformat(),
            "conversation_id": u.conversation_id,
        }
        for u in usages
    ]
