"""Contracts for the Member 3 emergency-workflow prototype."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from ml.safety import SafetyAction


class EmergencyState(str, Enum):
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    CAREGIVER_NOTIFICATION_RECORDED = "caregiver_notification_recorded"
    EMERGENCY_CONTACT_REQUESTED = "emergency_contact_requested"
    CANCELLED = "cancelled"
    RESOLVED = "resolved"


class EmergencyCommand(str, Enum):
    CONFIRM = "confirm"
    RECORD_CAREGIVER_NOTIFICATION = "record_caregiver_notification"
    REQUEST_EMERGENCY_CONTACT = "request_emergency_contact"
    CANCEL = "cancel"
    RESOLVE = "resolve"


def _clean(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    result = " ".join(value.split())
    if not result:
        raise ValueError(f"{label} must not be blank")
    return result


class EmergencyStartRequest(BaseModel):
    user_id: Annotated[str, Field(min_length=1, max_length=128)]
    alert_id: Annotated[str, Field(min_length=1, max_length=128)]
    safety_action: SafetyAction
    safety_reason: Annotated[str, Field(min_length=1, max_length=1000)]
    evidence: Annotated[list[str], Field(min_length=1, max_length=25)]
    caregiver_contact_id: str | None = Field(default=None, max_length=128)

    @field_validator("user_id", "alert_id", "safety_reason", mode="before")
    @classmethod
    def clean_text(cls, value: str, info):  # noqa: ANN001
        return _clean(value, info.field_name)

    @field_validator("caregiver_contact_id", mode="before")
    @classmethod
    def clean_optional_contact(cls, value):  # noqa: ANN001
        return None if value is None else _clean(value, "caregiver_contact_id")

    @field_validator("evidence", mode="before")
    @classmethod
    def clean_evidence(cls, value):  # noqa: ANN001
        if not isinstance(value, list):
            raise ValueError("evidence must be a list")
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = _clean(item, "evidence item")
            if cleaned.casefold() not in seen:
                seen.add(cleaned.casefold())
                result.append(cleaned)
        if not result:
            raise ValueError("evidence must contain at least one usable item")
        return result

    @model_validator(mode="after")
    def require_emergency_action(self) -> "EmergencyStartRequest":
        if self.safety_action != SafetyAction.EMERGENCY_ESCALATION:
            raise ValueError(
                "emergency workflow requires emergency_escalation from the safety engine"
            )
        return self

    model_config = {"frozen": True}


class EmergencyCommandRequest(BaseModel):
    command: EmergencyCommand
    actor_id: Annotated[str, Field(min_length=1, max_length=128)]
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("actor_id", mode="before")
    @classmethod
    def clean_actor(cls, value: str) -> str:
        return _clean(value, "actor_id")

    @field_validator("note", mode="before")
    @classmethod
    def clean_note(cls, value):  # noqa: ANN001
        return None if value is None else _clean(value, "note")

    model_config = {"frozen": True}


class EmergencyAuditEvent(BaseModel):
    sequence: int = Field(ge=1)
    event: str
    actor_id: str
    note: str | None
    occurred_at: datetime

    model_config = {"frozen": True}


class EmergencyWorkflowRecord(BaseModel):
    workflow_id: str
    user_id: str
    alert_id: str
    state: EmergencyState
    safety_action: SafetyAction
    safety_reason: str
    evidence: tuple[str, ...]
    caregiver_contact_id: str | None
    urgent_instruction: str
    external_action_performed: bool
    audit_events: tuple[EmergencyAuditEvent, ...]
    created_at: datetime
    updated_at: datetime

    model_config = {"frozen": True}


class EmergencyListResponse(BaseModel):
    user_id: str
    workflows: list[EmergencyWorkflowRecord]
    count: int

    @model_validator(mode="after")
    def validate_count(self) -> "EmergencyListResponse":
        if self.count != len(self.workflows):
            raise ValueError("count must match workflows length")
        return self


def new_workflow_id() -> str:
    return str(uuid.uuid4())
