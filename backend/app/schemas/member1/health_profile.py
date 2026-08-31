"""Minimal Member 1 contracts required by the shared backend bootstrap."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthProfileCreate(BaseModel):
    user_id: int = Field(gt=0)
    age: int | None = Field(default=None, ge=0, le=130)
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=1000)
    known_conditions: list[str] = Field(default_factory=list, max_length=100)
    medications: list[str] = Field(default_factory=list, max_length=100)
    allergies: list[str] = Field(default_factory=list, max_length=100)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HealthProfileResponse(HealthProfileCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, extra="forbid")
