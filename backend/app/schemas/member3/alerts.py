"""Validated API contracts for the Member 3 alert system."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from ml.safety import SafetyAction


class AlertPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


def _clean_text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned


class AlertEvaluationRequest(BaseModel):
    """A precomputed safety decision submitted for alert evaluation."""

    user_id: Annotated[str, Field(min_length=1, max_length=128)]
    event_id: Annotated[str, Field(min_length=1, max_length=128)]
    safety_action: SafetyAction
    safety_reason: Annotated[str, Field(min_length=1, max_length=1000)]
    evidence: Annotated[list[str], Field(min_length=1, max_length=25)]
    occurred_at: datetime

    @field_validator("user_id", "event_id", "safety_reason", mode="before")
    @classmethod
    def clean_required_text(cls, value: str, info):  # noqa: ANN001
        return _clean_text(value, info.field_name)

    @field_validator("evidence", mode="before")
    @classmethod
    def clean_evidence(cls, value):  # noqa: ANN001
        if not isinstance(value, list):
            raise ValueError("evidence must be a list")
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            normalized = _clean_text(item, "evidence item")
            key = normalized.casefold()
            if key not in seen:
                seen.add(key)
                cleaned.append(normalized)
        if not cleaned:
            raise ValueError("evidence must contain at least one usable item")
        return cleaned

    model_config = {"frozen": True}


class AlertRecord(BaseModel):
    alert_id: str
    user_id: str
    event_id: str
    safety_action: SafetyAction
    priority: AlertPriority
    status: AlertStatus
    title: str
    message: str
    evidence: list[str]
    requires_human_confirmation: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"frozen": True}


class AlertEvaluationResponse(BaseModel):
    created: bool
    suppressed_reason: str | None = None
    alert: AlertRecord | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "AlertEvaluationResponse":
        if self.created == (self.alert is None):
            raise ValueError("created must match alert presence")
        if self.created and self.suppressed_reason is not None:
            raise ValueError("created alerts cannot have a suppression reason")
        if not self.created and not self.suppressed_reason:
            raise ValueError("suppressed alerts require a reason")
        return self


class AlertStatusUpdateRequest(BaseModel):
    status: AlertStatus


class AlertListResponse(BaseModel):
    user_id: str
    alerts: list[AlertRecord]
    count: int

    @model_validator(mode="after")
    def validate_count(self) -> "AlertListResponse":
        if self.count != len(self.alerts):
            raise ValueError("count must match alerts length")
        return self


def new_alert_id() -> str:
    return str(uuid.uuid4())
