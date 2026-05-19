from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from meditatio.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "aeris"}


@router.get("/health/db")
async def db_health_check(session: AsyncSession = Depends(get_session)):
    """Database health check endpoint."""
    try:
        result = await session.execute(text("SELECT 1"))
        await result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
