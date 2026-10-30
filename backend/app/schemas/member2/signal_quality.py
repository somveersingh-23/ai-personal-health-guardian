"""Record-integrity, sampled-signal, and camera-frame quality contracts."""

from datetime import datetime
from math import isfinite
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.member2.common import (
    FreshnessStatus,
    IntegrityStatus,
    SignalQualityStatus,
    ValidationFlag,
)
from app.schemas.member2.health_event import STRICT_CONFIG, ReadingCreate
from app.schemas.member2.quality_vector import QualityVector


class RecordIntegrityAssessmentRequest(BaseModel):
    reading: ReadingCreate
    received_at: datetime
    model_config = STRICT_CONFIG

    @field_validator("received_at")
    @classmethod
    def aware_received_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("received_at must include a UTC offset")
        return value


class QualityAssessmentResponse(BaseModel):
    record_integrity_score: float = Field(ge=0.0, le=1.0)
    record_integrity_status: IntegrityStatus
    signal_quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    signal_quality_status: SignalQualityStatus = SignalQualityStatus.UNKNOWN
    freshness_status: FreshnessStatus
    data_freshness_seconds: int = Field(ge=0)
    validation_flag: ValidationFlag
    validation_reason: str | None = Field(default=None, max_length=512)
    remeasure_recommended: bool = False
    policy_version: str = Field(min_length=1, max_length=64)
    assessment_details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    quality_vector: QualityVector
    model_config = STRICT_CONFIG


class WaveformQualityAssessmentRequest(BaseModel):
    samples: list[float] = Field(min_length=32, max_length=30_000)
    sampling_rate_hz: float = Field(ge=10.0, le=2000.0)
    motion_reference: list[float] | None = Field(default=None, min_length=32, max_length=30_000)
    model_config = STRICT_CONFIG

    @field_validator("samples", "motion_reference")
    @classmethod
    def finite_samples(cls, values: list[float] | None) -> list[float] | None:
        if values is not None and not all(isfinite(value) for value in values):
            raise ValueError("waveform values must be finite")
        return values

    @model_validator(mode="after")
    def aligned_motion(self) -> "WaveformQualityAssessmentRequest":
        if self.motion_reference is not None and len(self.motion_reference) != len(self.samples):
            raise ValueError("motion_reference must contain one value per signal sample")
        return self


class WaveformQualityResponse(BaseModel):
    signal_quality_score: float = Field(ge=0.0, le=1.0)
    signal_quality_status: SignalQualityStatus
    clipping_fraction: float = Field(ge=0.0, le=1.0)
    flatline_fraction: float = Field(ge=0.0, le=1.0)
    motion_correlation: float | None = Field(default=None, ge=-1.0, le=1.0)
    usable: bool
    policy_version: Literal["waveform-sqi-v1"] = "waveform-sqi-v1"
    non_diagnostic: Literal[True] = True
    model_config = STRICT_CONFIG


class CameraFrameQualityRequest(BaseModel):
    mean_luminance: float = Field(ge=0.0, le=255.0)
    luminance_stddev: float = Field(ge=0.0, le=128.0)
    blur_variance: float = Field(ge=0.0, le=1_000_000.0)
    motion_score: float = Field(ge=0.0, le=1.0)
    clipped_dark_fraction: float = Field(ge=0.0, le=1.0)
    clipped_bright_fraction: float = Field(ge=0.0, le=1.0)
    model_config = STRICT_CONFIG


class CameraFrameQualityResponse(BaseModel):
    accepted: bool
    score: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(max_length=10)
    guidance: list[str] = Field(max_length=10)
    policy_version: Literal["camera-capture-quality-v1"] = "camera-capture-quality-v1"
    non_diagnostic: Literal[True] = True
    model_config = STRICT_CONFIG


QualityAssessmentRequest = RecordIntegrityAssessmentRequest
