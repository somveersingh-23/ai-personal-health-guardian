"""End-to-end Member 3 Guardian orchestration contracts."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.schemas.member3.alerts import AlertEvaluationResponse
from app.schemas.member3.assistant import EvidenceItem
from app.schemas.member3.emergency import EmergencyWorkflowRecord
from app.schemas.member3.insights import InsightRecord
from app.schemas.member3.notifications import (
    NotificationBatchResponse,
    NotificationChannel,
)
from ml.safety import SafetyAction


def _clean(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned


class GuardianProcessRequest(BaseModel):
    user_id: Annotated[str, Field(min_length=1, max_length=128)]
    event_id: Annotated[str, Field(min_length=1, max_length=128)]
    insight_type: Annotated[str, Field(min_length=1, max_length=64)] = "recovery"
    deviation_score: float = Field(ge=0)
    confidence: float
    signal_quality: float
    evidence: Annotated[list[EvidenceItem], Field(min_length=1, max_length=25)]
    critical_flags: list[str] = Field(default_factory=list, max_length=25)
    user_confirmed_severe_symptoms: bool = False
    occurred_at: datetime
    notification_channels: list[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.IN_APP], max_length=3
    )
    consented_channels: list[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.IN_APP], max_length=3
    )
    channel_targets: dict[NotificationChannel, str] = Field(default_factory=dict)
    caregiver_contact_id: str | None = Field(default=None, max_length=128)

    @field_validator("user_id", "event_id", "insight_type", mode="before")
    @classmethod
    def clean_strings(cls, value: str, info):  # noqa: ANN001
        return _clean(value, info.field_name)

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
    def fractions(cls, value: float, info) -> float:  # noqa: ANN001
        if not 0 <= value <= 1:
            raise ValueError(f"{info.field_name} must be between 0 and 1")
        return value

    @field_validator("critical_flags", mode="before")
    @classmethod
    def clean_flags(cls, value):  # noqa: ANN001
        if not isinstance(value, list):
            raise ValueError("critical_flags must be a list")
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = _clean(item, "critical flag")
            if cleaned.casefold() not in seen:
                seen.add(cleaned.casefold())
                result.append(cleaned)
        return result

    @field_validator("caregiver_contact_id", mode="before")
    @classmethod
    def clean_contact(cls, value):  # noqa: ANN001
        return None if value is None else _clean(value, "caregiver_contact_id")

    model_config = {"frozen": True}


class GuardianProcessResponse(BaseModel):
    user_id: str
    event_id: str
    safety_action: SafetyAction
    safety_reason: str
    insight: InsightRecord
    alert: AlertEvaluationResponse
    notifications: NotificationBatchResponse | None
    emergency_workflow: EmergencyWorkflowRecord | None
    processed_at: datetime

    model_config = {"frozen": True}
