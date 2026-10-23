from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.models.member1.health_event import HealthEvent
from app.schemas.member1.health_event import (
    HealthEventCreate,
    HealthEventResponse,
    HealthEventUpdate,
)

router = APIRouter(
    prefix="/api/v1/member1/health-events",
    tags=["Member 1 - Health Events"],
)


@router.post("", response_model=HealthEventResponse, status_code=status.HTTP_201_CREATED)
async def create_health_event(
    payload: HealthEventCreate,
    db: AsyncSession = Depends(get_db),
):
    event = HealthEvent(**payload.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("", response_model=list[HealthEventResponse])
async def list_health_events(
    user_id: int = Query(gt=0),
    event_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=400, detail="start_time must be <= end_time")

    stmt = select(HealthEvent).where(HealthEvent.user_id == user_id)
    if event_type:
        stmt = stmt.where(HealthEvent.event_type == event_type.strip().lower())
    if start_time:
        stmt = stmt.where(HealthEvent.event_time >= start_time)
    if end_time:
        stmt = stmt.where(HealthEvent.event_time <= end_time)

    stmt = stmt.order_by(HealthEvent.event_time.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=HealthEventResponse)
async def get_health_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HealthEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Health event not found")
    return event


@router.patch("/{event_id}", response_model=HealthEventResponse)
async def update_health_event(
    event_id: int,
    payload: HealthEventUpdate,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HealthEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Health event not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, key, value)

    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(HealthEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Health event not found")
    await db.delete(event)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
