from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member1.health_event import HealthEvent


class HealthTimelineService:
    async def get_timeline(
        self,
        db: AsyncSession,
        user_id: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[HealthEvent]:
        stmt = select(HealthEvent).where(HealthEvent.user_id == user_id)
        if start_time:
            stmt = stmt.where(HealthEvent.event_time >= start_time)
        if end_time:
            stmt = stmt.where(HealthEvent.event_time <= end_time)
        stmt = stmt.order_by(HealthEvent.event_time.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())
