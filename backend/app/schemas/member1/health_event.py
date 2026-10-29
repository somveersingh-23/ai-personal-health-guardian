from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthEventCreate(BaseModel):
    user_id: int = Field(
        gt=0,
    )

    event_type: str = Field(
        min_length=1,
        max_length=50,
    )

    event_time: datetime

    value: float | None = None

    unit: str | None = Field(
        default=None,
        max_length=30,
    )

    source: str | None = Field(
        default=None,
        max_length=50,
    )

    notes: str | None = None

    metadata_json: dict | None = None


class HealthEventUpdate(BaseModel):
    event_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    event_time: datetime | None = None

    value: float | None = None

    unit: str | None = Field(
        default=None,
        max_length=30,
    )

    source: str | None = Field(
        default=None,
        max_length=50,
    )

    notes: str | None = None

    metadata_json: dict | None = None


class HealthEventResponse(BaseModel):
    id: int
    user_id: int
    event_type: str
    event_time: datetime
    value: float | None
    unit: str | None
    source: str | None
    notes: str | None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )