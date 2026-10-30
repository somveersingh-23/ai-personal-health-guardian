"""Notification intent and delivery-receipt contracts for Member 3."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.member3.alerts import AlertPriority


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    PUSH = "push"
    SMS = "sms"


class NotificationStatus(str, Enum):
    QUEUED = "queued"
    DISPATCH_REQUESTED = "dispatch_requested"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryOutcome(str, Enum):
    DELIVERED = "delivered"
    FAILED = "failed"


def _clean(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned


class NotificationCreateRequest(BaseModel):
    user_id: Annotated[str, Field(min_length=1, max_length=128)]
    source_event_id: Annotated[str, Field(min_length=1, max_length=128)]
    title: Annotated[str, Field(min_length=1, max_length=160)]
    body: Annotated[str, Field(min_length=1, max_length=1000)]
    priority: AlertPriority
    channels: Annotated[list[NotificationChannel], Field(min_length=1, max_length=3)]
    consented_channels: list[NotificationChannel] = Field(default_factory=list, max_length=3)
    channel_targets: dict[NotificationChannel, str] = Field(default_factory=dict)

    @field_validator("user_id", "source_event_id", "title", "body", mode="before")
    @classmethod
    def clean_strings(cls, value: str, info):  # noqa: ANN001
        return _clean(value, info.field_name)

    @field_validator("channels", "consented_channels", mode="after")
    @classmethod
    def unique_channels(cls, value):  # noqa: ANN001
        return list(dict.fromkeys(value))

    @field_validator("channel_targets", mode="before")
    @classmethod
    def clean_targets(cls, value):  # noqa: ANN001
        if not isinstance(value, dict):
            raise ValueError("channel_targets must be an object")
        return {key: _clean(target, "channel target") for key, target in value.items()}

    model_config = {"frozen": True}


class NotificationRecord(BaseModel):
    notification_id: str
    user_id: str
    source_event_id: str
    title: str
    body: str
    priority: AlertPriority
    channel: NotificationChannel
    target_ref: str | None
    status: NotificationStatus
    attempt_count: int = Field(ge=0)
    provider_receipt_id: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"frozen": True}


class NotificationBatchResponse(BaseModel):
    notifications: list[NotificationRecord]
    suppressed_channels: dict[str, str]
    count: int

    @model_validator(mode="after")
    def validate_count(self) -> "NotificationBatchResponse":
        if self.count != len(self.notifications):
            raise ValueError("count must match notifications length")
        return self


class DeliveryReceiptRequest(BaseModel):
    outcome: DeliveryOutcome
    provider_receipt_id: str | None = Field(default=None, max_length=256)
    failure_reason: str | None = Field(default=None, max_length=1000)

    @field_validator("provider_receipt_id", "failure_reason", mode="before")
    @classmethod
    def clean_optional(cls, value, info):  # noqa: ANN001
        return None if value is None else _clean(value, info.field_name)

    @model_validator(mode="after")
    def validate_outcome_fields(self) -> "DeliveryReceiptRequest":
        if self.outcome == DeliveryOutcome.DELIVERED and not self.provider_receipt_id:
            raise ValueError("delivered outcome requires provider_receipt_id")
        if self.outcome == DeliveryOutcome.FAILED and not self.failure_reason:
            raise ValueError("failed outcome requires failure_reason")
        return self

    model_config = {"frozen": True}


class NotificationListResponse(BaseModel):
    user_id: str
    notifications: list[NotificationRecord]
    count: int

    @model_validator(mode="after")
    def validate_count(self) -> "NotificationListResponse":
        if self.count != len(self.notifications):
            raise ValueError("count must match notifications length")
        return self


def new_notification_id() -> str:
    return str(uuid.uuid4())
