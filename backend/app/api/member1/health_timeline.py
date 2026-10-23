from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.schemas.member1.health_timeline import HealthTimelineResponse, TimelineEvent
from app.services.member1.health_timeline import HealthTimelineService

router = APIRouter(
    prefix="/api/v1/member1/health-timeline",
    tags=["Member 1 - Health Timeline"],
)
service = HealthTimelineService()


@router.get("/{user_id}", response_model=HealthTimelineResponse)
async def get_health_timeline(
    user_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="user_id must be positive")
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=400, detail="start_time must be <= end_time")

    events = await service.get_timeline(
        db, user_id, start_time, end_time, limit, offset
    )
    return HealthTimelineResponse(
        user_id=user_id,
        count=len(events),
        events=[TimelineEvent.model_validate(event) for event in events],
        start_time=start_time,
        end_time=end_time,
    )
