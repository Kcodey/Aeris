from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, desc

from aeris.models.trace import LLMTrace
from aeris.models.message import Message
from aeris.models.conversation import Conversation


class MonitoringService:
    """Monitoring and analytics service."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard_stats(self, hours: int = 168) -> Dict[str, Any]:
        """Get dashboard statistics."""
        since = datetime.utcnow() - timedelta(hours=hours)

        # Message counts
        message_result = await self.session.execute(
            select(func.count(Message.id))
            .where(Message.created_at >= since)
        )
        total_messages = message_result.scalar() or 0

        # Token usage (from LLMTrace for consistency with daily stats)
        token_result = await self.session.execute(
            select(
                func.sum(LLMTrace.input_tokens),
                func.sum(LLMTrace.output_tokens),
            )
            .where(LLMTrace.timestamp >= since)
        )
        row = token_result.first()
        input_tokens = row[0] or 0
        output_tokens = row[1] or 0

        # Conversation counts
        conv_result = await self.session.execute(
            select(func.count(Conversation.id))
            .where(Conversation.created_at >= since)
        )
        total_conversations = conv_result.scalar() or 0

        # Average first token latency
        latency_result = await self.session.execute(
            select(func.avg(LLMTrace.first_token_ms))
            .where(LLMTrace.timestamp >= since)
            .where(LLMTrace.first_token_ms.isnot(None))
        )
        avg_latency = latency_result.scalar() or 0

        return {
            "period_hours": hours,
            "total_messages": total_messages,
            "total_conversations": total_conversations,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "total_tokens": int(input_tokens + output_tokens),
            "avg_latency_ms": round(avg_latency, 2),
        }

    async def get_traces(
        self,
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        provider: Optional[str] = None,
        error_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[LLMTrace]:
        """Get LLM traces with filters."""
        query = select(LLMTrace).order_by(desc(LLMTrace.timestamp))

        if user_id:
            query = query.where(LLMTrace.user_id == user_id)
        if conversation_id:
            query = query.where(LLMTrace.conversation_id == conversation_id)
        if provider:
            query = query.where(LLMTrace.provider == provider)
        if error_only:
            query = query.where(LLMTrace.error_type.isnot(None))

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_trace_detail(self, trace_id: str) -> Optional[LLMTrace]:
        """Get single trace detail."""
        result = await self.session.execute(
            select(LLMTrace).where(LLMTrace.trace_id == trace_id)
        )
        return result.scalar_one_or_none()

    async def get_model_usage(self, hours: int = 168) -> List[Dict[str, Any]]:
        """Get usage by model."""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.session.execute(
            select(
                LLMTrace.provider,
                LLMTrace.model,
                func.count(LLMTrace.trace_id).label('count'),
                func.sum(LLMTrace.input_tokens).label('input_tokens'),
                func.sum(LLMTrace.output_tokens).label('output_tokens'),
                func.avg(LLMTrace.first_token_ms).label('avg_first_token_ms'),
                func.avg(LLMTrace.tokens_per_second).label('avg_tokens_per_second'),
            )
            .where(LLMTrace.timestamp >= since)
            .where(LLMTrace.first_token_ms.isnot(None))
            .group_by(LLMTrace.provider, LLMTrace.model)
            .order_by(desc('count'))
        )

        return [
            {
                "provider": row[0],
                "model": row[1],
                "count": row[2],
                "input_tokens": int(row[3] or 0),
                "output_tokens": int(row[4] or 0),
                "avg_first_token_ms": round(row[5] or 0, 2),
                "avg_tokens_per_second": round(row[6] or 0, 2),
            }
            for row in result.all()
        ]

    async def get_daily_stats(self, hours: int = 168) -> Dict[str, Any]:
        """Get daily token usage and latency distribution."""
        from sqlalchemy import Date, cast
        since = datetime.utcnow() - timedelta(hours=hours)

        # Daily token usage aggregated from LLMTrace
        daily_result = await self.session.execute(
            select(
                func.date(LLMTrace.timestamp).label("date"),
                func.sum(LLMTrace.input_tokens).label("input_tokens"),
                func.sum(LLMTrace.output_tokens).label("output_tokens"),
            )
            .where(LLMTrace.timestamp >= since)
            .group_by(func.date(LLMTrace.timestamp))
            .order_by(func.date(LLMTrace.timestamp))
        )

        daily_tokens = [
            {
                "date": row[0].strftime("%m/%d") if row[0] else "",
                "tokens": int((row[1] or 0) + (row[2] or 0)),
            }
            for row in daily_result.all()
        ]

        # Latency distribution from LLMTrace (first_token_ms)
        latency_ranges = [
            (0, 100, "0-100ms"),
            (100, 300, "100-300ms"),
            (300, 500, "300-500ms"),
            (500, 1000, "500ms-1s"),
            (1000, 3000, "1s-3s"),
            (3000, None, "3s以上"),
        ]

        latency_distribution = []
        for low, high, label in latency_ranges:
            query = select(func.count(LLMTrace.trace_id)).where(
                LLMTrace.timestamp >= since,
                LLMTrace.first_token_ms >= low,
                LLMTrace.first_token_ms.isnot(None),
            )
            if high is not None:
                query = query.where(LLMTrace.first_token_ms < high)
            count_result = await self.session.execute(query)
            latency_distribution.append({
                "range": label,
                "count": count_result.scalar() or 0,
            })

        return {
            "period_hours": hours,
            "daily_tokens": daily_tokens,
            "latency_distribution": latency_distribution,
        }
