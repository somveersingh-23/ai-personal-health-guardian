from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.models.member1.health_profile import HealthProfile
from app.schemas.member1.health_profile import (
    HealthProfileCreate,
    HealthProfileResponse,
)


router = APIRouter(
    prefix="/api/v1/member1/health-profile",
    tags=["Member 1 - Health Profile"],
)


@router.post(
    "",
    response_model=HealthProfileResponse,
)
async def create_health_profile(
    profile_data: HealthProfileCreate,
    db: AsyncSession = Depends(get_db),
):

    profile = HealthProfile(
        user_id=profile_data.user_id,
        age=profile_data.age,
        height_cm=profile_data.height_cm,
        weight_kg=profile_data.weight_kg,
        known_conditions=profile_data.known_conditions,
        medications=profile_data.medications,
        allergies=profile_data.allergies,
    )

    db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return profile


@router.get(
    "/{user_id}",
    response_model=HealthProfileResponse,
)
async def get_health_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(HealthProfile)
        .where(HealthProfile.user_id == user_id)
    )

    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Health profile not found",
        )

    return profile