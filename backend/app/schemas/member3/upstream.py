"""Stable contracts consumed from Member 1 and Member 2 without importing their code."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class BaselineResult(BaseModel):
    user_id: Annotated[str, Field(min_length=1, max_length=128)]
    event_id: Annotated[str, Field(min_length=1, max_length=128)]
    metric: Annotated[str, Field(min_length=1, max_length=64)]
    baseline: float
    current: float
    unit: Annotated[str, Field(min_length=1, max_length=32)]
    deviation_score: float = Field(ge=0)
    status: str
    confidence: float = Field(ge=0, le=1)
    occurred_at: datetime

    @field_validator("baseline", "current", "deviation_score", "confidence")
    @classmethod
    def reject_non_finite(cls, value: float) -> float:
        import math
        if not math.isfinite(value):
            raise ValueError("numeric values must be finite")
        return value

    model_config = {"frozen": True}


class SensorIntelligenceResult(BaseModel):
    event_id: Annotated[str, Field(min_length=1, max_length=128)]
    user_id: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    signal_quality: float = Field(ge=0, le=1)
    fusion_confidence: float = Field(ge=0, le=1)
    critical_flags: list[str] = Field(default_factory=list, max_length=25)
    user_confirmed_severe_symptoms: bool = False

    @field_validator("signal_quality", "fusion_confidence")
    @classmethod
    def reject_non_finite(cls, value: float) -> float:
        import math
        if not math.isfinite(value):
            raise ValueError("numeric values must be finite")
        return value

    model_config = {"frozen": True}
