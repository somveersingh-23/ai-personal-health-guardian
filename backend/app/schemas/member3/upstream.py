"""Stable contracts consumed from Member 1 and Member 2 without importing their code."""

from datetime import datetime
from math import isfinite
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MetricType = Literal[
    "heart_rate",
    "resting_heart_rate",
    "hrv_rmssd",
    "spo2",
    "respiration_rate",
    "skin_temperature",
    "steps",
    "sleep_duration",
    "active_calories",
]

STRICT_UPSTREAM_CONFIG = ConfigDict(frozen=True, extra="forbid")


class M2EvidenceItem(BaseModel):
    """Exact, import-free copy of Member 2's evidence item contract."""

    metric: MetricType
    direction: Literal["below", "normal", "above", "unknown"]
    standardized_deviation: float
    evidence_weight: float = Field(ge=0.0, le=1.0)
    quality_weight: float = Field(ge=0.0, le=1.0)

    @field_validator("standardized_deviation", "evidence_weight", "quality_weight")
    @classmethod
    def finite_numbers(cls, value: float) -> float:
        if isinstance(value, bool) or not isfinite(value):
            raise ValueError("evidence values must be finite")
        return value

    model_config = STRICT_UPSTREAM_CONFIG


class M2MultimodalEvidenceVector(BaseModel):
    """Frozen boundary contract emitted by Member 2 (schema v2.0.0)."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    user_id: int = Field(gt=0)
    window_start: datetime
    window_end: datetime
    evidence: list[M2EvidenceItem] = Field(max_length=50)
    combined_evidence_strength: float = Field(ge=0.0, le=1.0)
    missing_baselines: list[MetricType]
    abstained: bool = False
    abstention_reasons: list[str] = Field(default_factory=list, max_length=32)
    non_diagnostic: Literal[True] = True

    @field_validator("combined_evidence_strength")
    @classmethod
    def finite_strength(cls, value: float) -> float:
        if isinstance(value, bool) or not isfinite(value):
            raise ValueError("combined_evidence_strength must be finite")
        return value

    @model_validator(mode="after")
    def valid_window_and_abstention(self) -> "M2MultimodalEvidenceVector":
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("window timestamps must include UTC offsets")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if self.abstained and not self.abstention_reasons:
            raise ValueError("abstention_reasons are required when abstained is true")
        return self

    model_config = STRICT_UPSTREAM_CONFIG


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
