"""Resumable source-reconciliation session contracts for large histories."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.member2.common import SourceType

STRICT_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReconciliationSessionCreate(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    source: Literal[SourceType.HEALTH_CONNECT] = SourceType.HEALTH_CONNECT
    source_record_type: str = Field(min_length=1, max_length=128)
    window_start: datetime
    window_end: datetime
    model_config = STRICT_CONFIG

    @model_validator(mode="after")
    def validate_window(self) -> ReconciliationSessionCreate:
        for name, value in (("window_start", self.window_start), ("window_end", self.window_end)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must include a UTC offset")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if self.window_end - self.window_start > timedelta(days=31):
            raise ValueError("reconciliation window cannot exceed 31 days")
        return self


class ReconciliationSessionResponse(ReconciliationSessionCreate):
    status: Literal["collecting", "completed", "aborted"]
    received_record_count: int = Field(ge=0)
    tombstoned_stale_count: int = Field(default=0, ge=0)
    created_at: datetime
    expires_at: datetime
    completed_at: datetime | None = None
    model_config = STRICT_CONFIG


class ReconciliationRecordChunk(BaseModel):
    source_record_ids: list[str] = Field(min_length=1, max_length=500)
    model_config = STRICT_CONFIG

    @field_validator("source_record_ids")
    @classmethod
    def validate_ids(cls, value: list[str]) -> list[str]:
        if any(not 1 <= len(item) <= 256 for item in value):
            raise ValueError("every source record ID must contain 1-256 characters")
        if len(value) != len(set(value)):
            raise ValueError("source_record_ids must be unique within a chunk")
        return value


class ReconciliationChunkResponse(BaseModel):
    session_id: UUID
    received_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    total_unique_count: int = Field(ge=0)
    model_config = STRICT_CONFIG


class ReconciliationCompleteRequest(BaseModel):
    complete_snapshot: Literal[True]
    model_config = STRICT_CONFIG

    @field_validator("complete_snapshot", mode="before")
    @classmethod
    def require_true(cls, value: Any) -> bool:
        if value is not True:
            raise ValueError("complete_snapshot must be the boolean true")
        return True


class ReconciliationCompleteResponse(BaseModel):
    session_id: UUID
    authoritative_count: int = Field(ge=0)
    tombstoned_stale_count: int = Field(ge=0)
    completed_at: datetime
    model_config = STRICT_CONFIG


__all__ = [
    "ReconciliationChunkResponse",
    "ReconciliationCompleteRequest",
    "ReconciliationCompleteResponse",
    "ReconciliationRecordChunk",
    "ReconciliationSessionCreate",
    "ReconciliationSessionResponse",
]
