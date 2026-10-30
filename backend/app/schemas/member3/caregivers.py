"""Opaque caregiver relationship and consent contracts."""

import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class CaregiverLinkStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DECLINED = "declined"
    REVOKED = "revoked"


class CaregiverLinkCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    caregiver_user_ref: str = Field(min_length=1, max_length=128)
    relationship_label: str = Field(min_length=1, max_length=80)

    @field_validator("user_id", "caregiver_user_ref", "relationship_label", mode="before")
    @classmethod
    def clean(cls, value, info):  # noqa: ANN001
        if not isinstance(value, str) or not (cleaned := " ".join(value.split())):
            raise ValueError(f"{info.field_name} must not be blank")
        return cleaned

    model_config = {"frozen": True}


class CaregiverDecision(str, Enum):
    ACCEPT = "accept"
    DECLINE = "decline"
    REVOKE = "revoke"


class CaregiverDecisionRequest(BaseModel):
    decision: CaregiverDecision
    actor_user_ref: str = Field(min_length=1, max_length=128)

    @field_validator("actor_user_ref", mode="before")
    @classmethod
    def clean_actor(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not (cleaned := " ".join(value.split())):
            raise ValueError("actor_user_ref must not be blank")
        return cleaned


class CaregiverLink(BaseModel):
    link_id: str
    user_id: str
    caregiver_user_ref: str
    relationship_label: str
    status: CaregiverLinkStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"frozen": True}


class CaregiverListResponse(BaseModel):
    user_id: str
    links: list[CaregiverLink]
    count: int


def new_link_id() -> str:
    return str(uuid.uuid4())
