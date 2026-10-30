"""Privacy-conscious conversation contracts for the AI Guardian."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.member3.assistant import EvidenceItem
from ml.safety import SafetyAction


def _clean(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned


class ConversationMessageRequest(BaseModel):
    user_id: Annotated[str, Field(min_length=1, max_length=128)]
    message_id: Annotated[str, Field(min_length=1, max_length=128)]
    conversation_id: str | None = Field(default=None, max_length=128)
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    safety_action: SafetyAction
    safety_reason: Annotated[str, Field(min_length=1, max_length=1000)]
    evidence: Annotated[list[EvidenceItem], Field(min_length=1, max_length=25)]
    locale: str = "en"

    @field_validator(
        "user_id", "message_id", "question", "safety_reason", mode="before"
    )
    @classmethod
    def clean_text(cls, value: str, info):  # noqa: ANN001
        return _clean(value, info.field_name)

    @field_validator("conversation_id", mode="before")
    @classmethod
    def clean_optional_id(cls, value):  # noqa: ANN001
        return None if value is None else _clean(value, "conversation_id")

    model_config = {"frozen": True}


class ConversationTurn(BaseModel):
    message_id: str
    question: str
    answer: str
    safety_action: SafetyAction
    evidence_metrics: tuple[str, ...]
    disclaimer: str
    created_at: datetime

    model_config = {"frozen": True}


class ConversationRecord(BaseModel):
    conversation_id: str
    user_id: str
    turns: tuple[ConversationTurn, ...]
    created_at: datetime
    updated_at: datetime

    model_config = {"frozen": True}


class ConversationListResponse(BaseModel):
    user_id: str
    conversations: list[ConversationRecord]
    count: int

    @model_validator(mode="after")
    def validate_count(self) -> "ConversationListResponse":
        if self.count != len(self.conversations):
            raise ValueError("count must match conversations length")
        return self


class ConversationDeleteResponse(BaseModel):
    conversation_id: str
    deleted: bool


def new_conversation_id() -> str:
    return str(uuid.uuid4())
