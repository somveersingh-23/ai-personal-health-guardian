"""HTTP contracts for deterministic Member 3 safety evaluation."""

from __future__ import annotations

import math
from pydantic import BaseModel, Field, field_validator

from ml.safety import SafetyAction


class SafetyEvaluationRequest(BaseModel):
    deviation_score: float = Field(ge=0)
    confidence: float
    signal_quality: float
    evidence: list[str] = Field(default_factory=list, max_length=25)
    critical_flags: list[str] = Field(default_factory=list, max_length=25)
    user_confirmed_severe_symptoms: bool = False

    @field_validator("deviation_score", "confidence", "signal_quality", mode="before")
    @classmethod
    def finite_numbers(cls, value, info):  # noqa: ANN001
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{info.field_name} must be a finite number")
        if not math.isfinite(value):
            raise ValueError(f"{info.field_name} must be a finite number")
        return float(value)

    @field_validator("confidence", "signal_quality", mode="after")
    @classmethod
    def fraction(cls, value: float, info) -> float:  # noqa: ANN001
        if not 0 <= value <= 1:
            raise ValueError(f"{info.field_name} must be between 0 and 1")
        return value

    @field_validator("evidence", "critical_flags", mode="before")
    @classmethod
    def clean_string_lists(cls, value, info):  # noqa: ANN001
        if not isinstance(value, list):
            raise ValueError(f"{info.field_name} must be a list")
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"{info.field_name} must contain only strings")
            cleaned = " ".join(item.split())
            if not cleaned:
                continue
            if cleaned.casefold() not in seen:
                seen.add(cleaned.casefold())
                result.append(cleaned)
        return result

    model_config = {"frozen": True}


class SafetyEvaluationResponse(BaseModel):
    action: SafetyAction
    reason: str
    evidence: tuple[str, ...]
    requires_human_confirmation: bool
    disclaimer: str

    model_config = {"frozen": True}
