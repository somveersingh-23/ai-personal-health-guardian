from datetime import datetime

from pydantic import BaseModel, Field


class HealthProfileCreate(BaseModel):

    user_id: int

    age: int | None = Field(
        default=None,
        ge=0,
        le=120,
    )

    height_cm: float | None = Field(
        default=None,
        gt=0,
    )

    weight_kg: float | None = Field(
        default=None,
        gt=0,
    )

    known_conditions: list[str] = Field(
        default_factory=list,
    )

    medications: list[str] = Field(
        default_factory=list,
    )

    allergies: list[str] = Field(
        default_factory=list,
    )


class HealthProfileResponse(HealthProfileCreate):

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
