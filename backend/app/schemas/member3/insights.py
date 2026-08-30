"""Structured health-insight contracts owned by Member 3."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.member3.assistant import EvidenceItem
from ml.safety import SafetyAction


class InsightSeverity(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class InsightStatus(str, Enum):
    NEW = "new"
    VIEWED = "viewed"
    ARCHIVED = "archived"


def _clean(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned


class InsightCreateRequest(BaseModel):
    user_id: Annotated[str, Field(min_length=1, max_length=128)]
    source_event_id: Annotated[str, Field(min_length=1, max_length=128)]
    insight_type: Annotated[str, Field(min_length=1, max_length=64)]
    safety_action: SafetyAction
    safety_reason: Annotated[str, Field(min_length=1, max_length=1000)]
    evidence: Annotated[list[EvidenceItem], Field(min_length=1, max_length=25)]

    @field_validator(
        "user_id", "source_event_id", "insight_type", "safety_reason", mode="before"
    )
    @classmethod
    def clean_strings(cls, value: str, info):  # noqa: ANN001
        return _clean(value, info.field_name)

    @field_validator("insight_type", mode="after")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        return value.casefold().replace(" ", "_")

    model_config = {"frozen": True}


class InsightRecord(BaseModel):
    insight_id: str
    user_id: str
    source_event_id: str
    insight_type: str
    safety_action: SafetyAction
    severity: InsightSeverity
    status: InsightStatus
    title: str
    summary: str
    evidence: tuple[EvidenceItem, ...]
    limitations: tuple[str, ...]
    disclaimer: str
    created_at: datetime
    updated_at: datetime

    model_config = {"frozen": True}


class InsightStatusUpdateRequest(BaseModel):
    status: InsightStatus


class InsightListResponse(BaseModel):
    user_id: str
    insights: list[InsightRecord]
    count: int

    @model_validator(mode="after")
    def validate_count(self) -> "InsightListResponse":
        if self.count != len(self.insights):
            raise ValueError("count must match insights length")
        return self


def new_insight_id() -> str:
    return str(uuid.uuid4())
