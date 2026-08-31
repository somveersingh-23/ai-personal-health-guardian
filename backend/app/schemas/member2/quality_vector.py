"""Multidimensional, uncertainty-aware sensor quality contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.member2.common import QualityDecision

STRICT_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QualityVector(BaseModel):
    """Separates evidence dimensions that must not be hidden in one score.

    Null means the dimension was not observed. It is deliberately different
    from zero, which means the dimension was measured and failed.
    """

    policy_version: Literal["quality-vector-v2"] = "quality-vector-v2"
    decision: QualityDecision
    record_integrity_score: float = Field(ge=0.0, le=1.0)
    signal_quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance_confidence: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    coverage_score: float | None = Field(default=None, ge=0.0, le=1.0)
    wear_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    motion_artifact_score: float | None = Field(default=None, ge=0.0, le=1.0)
    calibration_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    device_validation_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list, max_length=32)
    model_config = STRICT_CONFIG

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("quality reason_codes must be unique")
        if any(not 1 <= len(item) <= 64 for item in value):
            raise ValueError("quality reason codes must contain 1-64 characters")
        return value


__all__ = ["QualityVector"]
