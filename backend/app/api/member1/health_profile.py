from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.models.member1.health_profile import HealthProfile
from app.schemas.member1.health_profile import HealthProfileCreate, HealthProfileResponse

router = APIRouter(
    prefix="/api/v1/member1/health-profile",
    tags=["Member 1 - Health Profile"],
)


@router.post("", response_model=HealthProfileResponse)
async def create_or_replace_health_profile(
    profile_data: HealthProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a user's profile, or update it if one already exists."""
    result = await db.execute(
        select(HealthProfile)
        .where(HealthProfile.user_id == profile_data.user_id)
        .order_by(HealthProfile.updated_at.desc(), HealthProfile.id.desc())
    )
    profile = result.scalars().first()
    values = profile_data.model_dump(exclude={"user_id"})

    if profile is None:
        profile = HealthProfile(user_id=profile_data.user_id, **values)
        db.add(profile)
    else:
        for field, value in values.items():
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/{user_id}", response_model=HealthProfileResponse)
async def get_health_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HealthProfile)
        .where(HealthProfile.user_id == user_id)
        .order_by(HealthProfile.updated_at.desc(), HealthProfile.id.desc())
    )
    profile = result.scalars().first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health profile not found",
        )
    return profile
