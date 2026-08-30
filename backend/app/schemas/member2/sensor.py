"""Device, Health Connect sync cursor, deletion, reconciliation, and audit schemas."""

from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.member2.common import PermissionState, SourceType


class DeviceInfo(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    manufacturer: str | None = Field(default=None, max_length=128)
    model: str | None = Field(default=None, max_length=128)
    firmware_version: str | None = Field(default=None, max_length=64)
    device_type: str | None = Field(default=None, max_length=64)
    source_type: SourceType = SourceType.HEALTH_CONNECT
    permission_state: PermissionState = PermissionState.UNAVAILABLE
    battery_level: float | None = Field(default=None, ge=0.0, le=100.0)
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    last_sync_time: datetime | None = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("last_sync_time")
    @classmethod
    def aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("last_sync_time must include a UTC offset")
        return value


class DeviceRegistrationRequest(BaseModel):
    device: DeviceInfo
    model_config = ConfigDict(extra="forbid")


class DeviceRegistrationResponse(DeviceInfo):
    id: int
    user_id: int
    manufacturer: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    device_type: str | None = None
    source_type: str
    permission_state: str
    battery_level: float | None = None
    capabilities: list[str] = Field(default_factory=list)
    last_sync_time: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class HealthConnectSyncCursor(BaseModel):
    record_type: str = Field(min_length=1, max_length=128)
    token_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    last_successful_sync_at: datetime
    model_config = ConfigDict(extra="forbid")

    @field_validator("last_successful_sync_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("last_successful_sync_at must include a UTC offset")
        return value


class HealthConnectSyncCursorResponse(BaseModel):
    id: int
    user_id: int
    record_type: str
    token_fingerprint: str = Field(min_length=64, max_length=64)
    last_successful_sync_at: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class SourceDeletionRequest(BaseModel):
    source: Literal[SourceType.HEALTH_CONNECT] = SourceType.HEALTH_CONNECT
    source_record_type: str = Field(min_length=1, max_length=128)
    source_record_ids: list[str] = Field(min_length=1, max_length=500)
    deleted_at: datetime | None = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("source_record_ids")
    @classmethod
    def validate_record_ids(cls, value: list[str]) -> list[str]:
        if any(not 1 <= len(item) <= 256 for item in value):
            raise ValueError("every source record ID must contain 1-256 characters")
        if len(value) != len(set(value)):
            raise ValueError("source_record_ids must be unique")
        return value

    @field_validator("deleted_at")
    @classmethod
    def validate_deleted_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("deleted_at must include a UTC offset")
        return value


class SourceDeletionResponse(BaseModel):
    requested_count: int = Field(ge=0)
    deleted_count: int = Field(ge=0)
    tombstoned_count: int = Field(default=0, ge=0)
    model_config = ConfigDict(extra="forbid")


class SourceReconciliationRequest(BaseModel):
    """Legacy bounded snapshot; new clients use staged reconciliation sessions."""

    source: Literal[SourceType.HEALTH_CONNECT] = SourceType.HEALTH_CONNECT
    source_record_type: str = Field(min_length=1, max_length=128)
    window_start: datetime
    window_end: datetime
    source_record_ids: list[str] = Field(default_factory=list, max_length=5000)
    complete_snapshot: Literal[True]
    model_config = ConfigDict(extra="forbid")

    @field_validator("complete_snapshot", mode="before")
    @classmethod
    def require_boolean_true(cls, value: Any) -> bool:
        if value is not True:
            raise ValueError("complete_snapshot must be the boolean true")
        return True

    @model_validator(mode="after")
    def validate_snapshot(self) -> "SourceReconciliationRequest":
        for name, value in (("window_start", self.window_start), ("window_end", self.window_end)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must include a UTC offset")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if self.window_end - self.window_start > timedelta(days=31):
            raise ValueError("reconciliation window cannot exceed 31 days")
        if any(not 1 <= len(item) <= 256 for item in self.source_record_ids):
            raise ValueError("every source record ID must contain 1-256 characters")
        if len(self.source_record_ids) != len(set(self.source_record_ids)):
            raise ValueError("source_record_ids must be unique")
        return self


class SourceReconciliationResponse(BaseModel):
    authoritative_count: int = Field(ge=0)
    deleted_stale_count: int = Field(ge=0)
    model_config = ConfigDict(extra="forbid")


class SensorIngestionAuditResponse(BaseModel):
    id: int
    payload_sha256: str
    payload_size_bytes: int
    event_count: int
    user_id: int
    source: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, extra="forbid")


# Alias for backward compatibility
RawSensorAuditResponse = SensorIngestionAuditResponse

SensorIngestionPayload = dict[str, Any]
RawSensorPayload = SensorIngestionPayload
