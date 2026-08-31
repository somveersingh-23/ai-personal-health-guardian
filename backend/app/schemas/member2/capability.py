"""Device capability and validation-registry contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.member2.common import (
    CalibrationStatus,
    DeviceSupportStatus,
    MetricType,
    RecordingMethod,
    SourceType,
)

STRICT_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DeviceCapabilityProfile(BaseModel):
    metric: MetricType
    source_record_type: str = Field(min_length=1, max_length=128)
    source_type: SourceType
    support_status: DeviceSupportStatus = DeviceSupportStatus.EXPERIMENTAL
    canonical_unit_ucum: str = Field(min_length=1, max_length=32)
    body_site: str | None = Field(default=None, max_length=64)
    sampling_rate_min_hz: float | None = Field(default=None, gt=0.0, le=10_000.0)
    sampling_rate_max_hz: float | None = Field(default=None, gt=0.0, le=10_000.0)
    measurement_resolution: float | None = Field(default=None, gt=0.0)
    recording_methods: list[RecordingMethod] = Field(default_factory=list, max_length=8)
    reference_method: str | None = Field(default=None, max_length=256)
    calibration_status: CalibrationStatus = CalibrationStatus.UNVERIFIED
    calibration_valid_until: datetime | None = None
    validation_protocol_version: str | None = Field(default=None, max_length=64)
    known_limitations: list[str] = Field(default_factory=list, max_length=32)
    model_config = STRICT_CONFIG

    @field_validator("calibration_valid_until")
    @classmethod
    def aware_calibration_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("calibration_valid_until must include a UTC offset")
        return value

    @field_validator("recording_methods", "known_limitations")
    @classmethod
    def unique_lists(cls, value: list) -> list:
        if len(value) != len(set(value)):
            raise ValueError("capability lists must contain unique values")
        return value

    @model_validator(mode="after")
    def validate_sampling_range(self) -> DeviceCapabilityProfile:
        if (
            self.sampling_rate_min_hz is not None
            and self.sampling_rate_max_hz is not None
            and self.sampling_rate_max_hz < self.sampling_rate_min_hz
        ):
            raise ValueError("sampling_rate_max_hz cannot be below sampling_rate_min_hz")
        if self.support_status == DeviceSupportStatus.SUPPORTED and not self.validation_protocol_version:
            raise ValueError("supported capability requires validation_protocol_version")
        if self.calibration_status == CalibrationStatus.VALID and not self.reference_method:
            raise ValueError("valid calibration requires a reference_method")
        return self


class DeviceCapabilityUpsertRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    capabilities: list[DeviceCapabilityProfile] = Field(min_length=1, max_length=100)
    model_config = STRICT_CONFIG

    @model_validator(mode="after")
    def unique_capabilities(self) -> DeviceCapabilityUpsertRequest:
        keys = [(item.metric, item.source_record_type) for item in self.capabilities]
        if len(keys) != len(set(keys)):
            raise ValueError("capabilities must be unique by metric and source_record_type")
        return self


class DeviceCapabilityResponse(DeviceCapabilityProfile):
    id: int
    user_id: int
    device_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class DeviceCapabilityBatchResponse(BaseModel):
    device_id: str
    capabilities: list[DeviceCapabilityResponse]
    model_config = STRICT_CONFIG


__all__ = [
    "DeviceCapabilityBatchResponse",
    "DeviceCapabilityProfile",
    "DeviceCapabilityResponse",
    "DeviceCapabilityUpsertRequest",
]
