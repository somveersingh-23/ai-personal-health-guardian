"""Versioned, source-faithful health record contracts for Member 2."""

from __future__ import annotations

import json
from datetime import datetime
from math import isfinite
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.member2.common import (
    CANONICAL_UCUM_UNITS,
    LOINC_CODES,
    METRIC_SPECS,
    EventLifecycleStatus,
    FreshnessStatus,
    IntegrityStatus,
    MetricType,
    MotionState,
    PermissionState,
    ProcessingPurpose,
    RecordingMethod,
    RetentionClass,
    SignalQualityStatus,
    SourceType,
    TemporalType,
    ValidationFlag,
    WearState,
)
from app.schemas.member2.quality_vector import QualityVector

MAX_METADATA_BYTES = 8 * 1024
MAX_METADATA_ITEMS = 32
STRICT_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _validate_json_depth(value: Any, depth: int = 0) -> None:
    if depth > 8:
        raise ValueError("metadata nesting cannot exceed 8 levels")
    if isinstance(value, dict):
        for nested in value.values():
            _validate_json_depth(nested, depth + 1)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _validate_json_depth(nested, depth + 1)


def _aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a UTC offset")
    return value


class SeriesSample(BaseModel):
    observed_at: datetime
    value: float
    model_config = STRICT_CONFIG

    @field_validator("observed_at")
    @classmethod
    def validate_time(cls, value: datetime) -> datetime:
        return _aware(value, "sample observed_at")

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError("sample value must be finite")
        return float(value)


class SessionStage(BaseModel):
    start_at: datetime
    end_at: datetime
    stage: Literal[
        "unknown", "awake", "awake_in_bed", "out_of_bed", "sleeping", "light", "deep", "rem"
    ]
    model_config = STRICT_CONFIG

    @model_validator(mode="after")
    def validate_interval(self) -> SessionStage:
        _aware(self.start_at, "stage start_at")
        _aware(self.end_at, "stage end_at")
        if self.end_at <= self.start_at:
            raise ValueError("stage end_at must be after start_at")
        return self


class ReadingBase(BaseModel):
    """Untrusted connector record. Production identity is added by the server."""

    schema_version: Literal["2.0.0", "3.0.0"] = "2.0.0"
    event_id: UUID = Field(default_factory=uuid4)
    metric: MetricType
    unit: str = Field(min_length=1, max_length=32)
    source: SourceType
    data_origin_package: str | None = Field(default=None, min_length=1, max_length=256)
    source_record_type: str | None = Field(default=None, min_length=1, max_length=128)
    source_record_id: str | None = Field(default=None, min_length=1, max_length=256)
    client_record_id: str | None = Field(default=None, min_length=1, max_length=256)
    client_record_version: int | None = Field(default=None, ge=0)
    source_last_modified_at: datetime | None = None
    device_id: str | None = Field(default=None, min_length=1, max_length=128)
    device_manufacturer: str | None = Field(default=None, min_length=1, max_length=128)
    device_model: str | None = Field(default=None, min_length=1, max_length=128)
    device_type: str | None = Field(default=None, min_length=1, max_length=64)
    body_site: str | None = Field(default=None, min_length=1, max_length=64)
    sampling_rate_hz: float | None = Field(default=None, gt=0.0, le=10_000.0)
    wear_state: WearState = WearState.UNKNOWN
    motion_state: MotionState = MotionState.UNKNOWN
    motion_artifact_score: float | None = Field(default=None, ge=0.0, le=1.0)
    recording_method: RecordingMethod = RecordingMethod.UNKNOWN
    permission_state: PermissionState = PermissionState.UNAVAILABLE
    consent_receipt_id: UUID | None = None
    processing_purpose: ProcessingPurpose = ProcessingPurpose.SENSOR_INTELLIGENCE_WELLNESS
    purpose_version: str | None = Field(default=None, min_length=1, max_length=64)
    retention_class: RetentionClass = RetentionClass.NORMALIZED_OBSERVATION
    mapper_version: str = Field(default="connector-mapper-v2", min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_config = STRICT_CONFIG

    @field_validator("source_last_modified_at")
    @classmethod
    def validate_modified_at(cls, value: datetime | None) -> datetime | None:
        return _aware(value, "source_last_modified_at") if value else value

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > MAX_METADATA_ITEMS:
            raise ValueError(f"metadata may contain at most {MAX_METADATA_ITEMS} keys")
        if any(not isinstance(key, str) or not 1 <= len(key) <= 64 for key in value):
            raise ValueError("metadata keys must be strings between 1 and 64 characters")
        _validate_json_depth(value)
        try:
            encoded = json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be finite JSON-compatible data") from exc
        if len(encoded) > MAX_METADATA_BYTES:
            raise ValueError(f"metadata must not exceed {MAX_METADATA_BYTES} encoded bytes")
        return value

    @model_validator(mode="after")
    def validate_common_contract(self) -> ReadingBase:
        spec = METRIC_SPECS[self.metric]
        if self.unit not in spec.units:
            allowed = ", ".join(sorted(spec.units))
            raise ValueError(f"unit for {self.metric.value} must be one of: {allowed}")
        if self.source == SourceType.HEALTH_CONNECT:
            required = {
                "data_origin_package": self.data_origin_package,
                "source_record_type": self.source_record_type,
                "source_record_id": self.source_record_id,
                "source_last_modified_at": self.source_last_modified_at,
            }
            missing = [name for name, item in required.items() if item is None]
            if missing:
                raise ValueError(
                    "Health Connect records require complete source identity: " + ", ".join(missing)
                )
            if self.recording_method == RecordingMethod.SYNTHETIC:
                raise ValueError("Health Connect records cannot use synthetic recording_method")
        if self.source == SourceType.SIMULATED:
            if self.recording_method != RecordingMethod.SYNTHETIC:
                raise ValueError("simulated records require recording_method='synthetic'")
            if self.permission_state != PermissionState.UNAVAILABLE:
                raise ValueError("simulated records require permission_state='unavailable'")
        if self.source == SourceType.RESEARCH_DATASET:
            required_research_identity = {
                "data_origin_package": self.data_origin_package,
                "source_record_type": self.source_record_type,
                "source_record_id": self.source_record_id,
                "device_id": self.device_id,
            }
            missing = [
                name for name, item in required_research_identity.items() if item is None
            ]
            if missing:
                raise ValueError(
                    "research dataset records require complete offline identity: "
                    + ", ".join(missing)
                )
            if not self.data_origin_package.startswith("research."):
                raise ValueError("research dataset package must use the 'research.' namespace")
            if self.permission_state != PermissionState.UNAVAILABLE:
                raise ValueError("research dataset records require permission_state='unavailable'")
            if self.recording_method != RecordingMethod.AUTOMATICALLY_RECORDED:
                raise ValueError(
                    "research dataset records require recording_method='automatically_recorded'"
                )
        if (
            self.source == SourceType.HEALTH_CONNECT
            and self.metric == MetricType.SKIN_TEMPERATURE
            and self.unit != "degC_delta"
        ):
            raise ValueError("Health Connect skin temperature records must use degC_delta")
        if self.schema_version == "3.0.0" and self.source in {
            SourceType.HEALTH_CONNECT,
            SourceType.WEARABLE_BLUETOOTH,
            SourceType.CAMERA,
        }:
            if self.consent_receipt_id is None or self.purpose_version is None:
                raise ValueError(
                    "v3 live sensor records require consent_receipt_id and purpose_version"
                )
        if self.wear_state == WearState.NOT_WORN and self.metric in {
            MetricType.HEART_RATE,
            MetricType.RESTING_HEART_RATE,
            MetricType.HRV_RMSSD,
            MetricType.SPO2,
            MetricType.RESPIRATION_RATE,
            MetricType.SKIN_TEMPERATURE,
        }:
            raise ValueError("physiological values must be omitted when the device is not worn")
        return self


class InstantReadingCreate(ReadingBase):
    temporal_type: Literal[TemporalType.INSTANT] = TemporalType.INSTANT
    observed_at: datetime
    timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    value: float

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        return _aware(value, "observed_at")

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError("value must be finite")
        return float(value)

    @model_validator(mode="after")
    def validate_shape(self) -> InstantReadingCreate:
        expected = METRIC_SPECS[self.metric].temporal_type
        if expected != TemporalType.INSTANT:
            raise ValueError(f"{self.metric.value} requires temporal_type='{expected.value}'")
        return self


class IntervalReadingCreate(ReadingBase):
    temporal_type: Literal[TemporalType.INTERVAL] = TemporalType.INTERVAL
    start_at: datetime
    end_at: datetime
    start_timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    end_timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    value: float

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError("value must be finite")
        return float(value)

    @model_validator(mode="after")
    def validate_shape(self) -> IntervalReadingCreate:
        _aware(self.start_at, "start_at")
        _aware(self.end_at, "end_at")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        expected = METRIC_SPECS[self.metric].temporal_type
        if expected != TemporalType.INTERVAL:
            raise ValueError(f"{self.metric.value} requires temporal_type='{expected.value}'")
        return self


class SeriesReadingCreate(ReadingBase):
    temporal_type: Literal[TemporalType.SERIES] = TemporalType.SERIES
    start_at: datetime
    end_at: datetime
    start_timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    end_timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    samples: list[SeriesSample] = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_shape(self) -> SeriesReadingCreate:
        _aware(self.start_at, "start_at")
        _aware(self.end_at, "end_at")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        expected = METRIC_SPECS[self.metric].temporal_type
        if expected != TemporalType.SERIES:
            raise ValueError(f"{self.metric.value} requires temporal_type='{expected.value}'")
        if any(not self.start_at <= sample.observed_at <= self.end_at for sample in self.samples):
            raise ValueError("every series sample must fall inside start_at/end_at")
        if any(a.observed_at >= b.observed_at for a, b in zip(self.samples, self.samples[1:], strict=False)):
            raise ValueError("series samples must be strictly time ordered")
        return self


class SessionReadingCreate(ReadingBase):
    temporal_type: Literal[TemporalType.SESSION] = TemporalType.SESSION
    start_at: datetime
    end_at: datetime
    start_timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    end_timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    stages: list[SessionStage] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_shape(self) -> SessionReadingCreate:
        _aware(self.start_at, "start_at")
        _aware(self.end_at, "end_at")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        expected = METRIC_SPECS[self.metric].temporal_type
        if expected != TemporalType.SESSION:
            raise ValueError(f"{self.metric.value} requires temporal_type='{expected.value}'")
        ordered = sorted(self.stages, key=lambda item: item.start_at)
        if any(stage.start_at < self.start_at or stage.end_at > self.end_at for stage in ordered):
            raise ValueError("every stage must fall inside the session")
        if any(a.end_at > b.start_at for a, b in zip(ordered, ordered[1:], strict=False)):
            raise ValueError("session stages must not overlap")
        return self


ReadingCreate = Annotated[
    InstantReadingCreate | IntervalReadingCreate | SeriesReadingCreate | SessionReadingCreate,
    Field(discriminator="temporal_type"),
]
ScalarReadingCreate = InstantReadingCreate


class HealthEventCreate(BaseModel):
    """Server-normalized event. Trust fields are never accepted by production ingestion."""

    schema_version: Literal["2.0.0", "3.0.0"] = "2.0.0"
    event_id: UUID
    user_id: int = Field(gt=0)
    temporal_type: TemporalType
    metric: MetricType
    unit: str
    source_unit: str
    canonical_unit_ucum: str
    standard_code_system: Literal["http://loinc.org"] | None = None
    standard_code: str | None = Field(default=None, max_length=32)
    source: SourceType
    observed_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    start_timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    end_timezone_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    value: float | None = None
    samples: list[SeriesSample] = Field(default_factory=list, max_length=10_000)
    stages: list[SessionStage] = Field(default_factory=list, max_length=500)
    data_origin_package: str
    source_record_type: str
    source_record_id: str | None = None
    client_record_id: str | None = None
    client_record_version: int | None = Field(default=None, ge=0)
    source_last_modified_at: datetime | None = None
    device_id: str | None = None
    device_manufacturer: str | None = None
    device_model: str | None = None
    device_type: str | None = None
    body_site: str | None = None
    sampling_rate_hz: float | None = Field(default=None, gt=0.0, le=10_000.0)
    wear_state: WearState = WearState.UNKNOWN
    motion_state: MotionState = MotionState.UNKNOWN
    motion_artifact_score: float | None = Field(default=None, ge=0.0, le=1.0)
    recording_method: RecordingMethod
    permission_state: PermissionState
    consent_receipt_id: UUID | None = None
    processing_purpose: ProcessingPurpose = ProcessingPurpose.SENSOR_INTELLIGENCE_WELLNESS
    purpose_version: str | None = None
    retention_class: RetentionClass = RetentionClass.NORMALIZED_OBSERVATION
    mapper_version: str = "connector-mapper-v2"
    metadata: dict[str, Any] = Field(default_factory=dict)
    record_integrity_score: float = Field(ge=0.0, le=1.0)
    record_integrity_status: IntegrityStatus
    signal_quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    signal_quality_status: SignalQualityStatus = SignalQualityStatus.UNKNOWN
    freshness_status: FreshnessStatus
    data_freshness_seconds: int = Field(ge=0)
    validation_flag: ValidationFlag
    validation_reason: str | None = Field(default=None, max_length=512)
    quality_vector: QualityVector
    quality_policy_version: str = Field(default="quality-vector-v2", min_length=1, max_length=64)
    lifecycle_status: EventLifecycleStatus = EventLifecycleStatus.ACTIVE
    deleted_at: datetime | None = None
    deletion_reason: str | None = Field(default=None, max_length=128)
    model_config = STRICT_CONFIG

    @model_validator(mode="after")
    def validate_normalized_shape(self) -> HealthEventCreate:
        spec = METRIC_SPECS[self.metric]
        if self.temporal_type != spec.temporal_type:
            raise ValueError("temporal_type does not match metric specification")
        if self.unit not in spec.units:
            raise ValueError("unit does not match metric specification")
        if self.source_unit != self.unit:
            raise ValueError("source_unit must preserve the connector unit")
        if self.canonical_unit_ucum != CANONICAL_UCUM_UNITS[self.metric]:
            raise ValueError("canonical_unit_ucum does not match metric specification")
        expected_loinc = LOINC_CODES[self.metric]
        if expected_loinc is None:
            if self.standard_code is not None or self.standard_code_system is not None:
                raise ValueError("metric does not have an approved standard-code mapping")
        elif self.standard_code != expected_loinc or self.standard_code_system != "http://loinc.org":
            raise ValueError("standard code does not match approved mapping")
        if self.temporal_type == TemporalType.INSTANT:
            if self.observed_at is None or self.value is None:
                raise ValueError("instant event requires observed_at and value")
        elif self.temporal_type == TemporalType.INTERVAL:
            if self.start_at is None or self.end_at is None or self.value is None:
                raise ValueError("interval event requires start_at, end_at and value")
        elif self.temporal_type == TemporalType.SERIES:
            if self.start_at is None or self.end_at is None or not self.samples:
                raise ValueError("series event requires start_at, end_at and samples")
        elif self.temporal_type == TemporalType.SESSION:
            if self.start_at is None or self.end_at is None:
                raise ValueError("session event requires start_at and end_at")
        if self.lifecycle_status == EventLifecycleStatus.DELETED:
            if self.deleted_at is None or self.deletion_reason is None:
                raise ValueError("deleted events require deleted_at and deletion_reason")
        elif self.deleted_at is not None or self.deletion_reason is not None:
            raise ValueError("active/corrected events cannot contain deletion metadata")
        return self


class HealthEventResponse(HealthEventCreate):
    id: int
    ingested_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class HealthEventBatchCreate(BaseModel):
    """Atomic production ingestion batch; user identity comes from authentication."""

    schema_version: Literal["2.0.0", "3.0.0"] = "2.0.0"
    batch_id: UUID = Field(default_factory=uuid4)
    events: list[ReadingCreate] = Field(min_length=1, max_length=500)
    model_config = STRICT_CONFIG

    @model_validator(mode="after")
    def consistent_versions(self) -> HealthEventBatchCreate:
        if any(event.schema_version != self.schema_version for event in self.events):
            raise ValueError("batch and event schema versions must match")
        return self


class HealthEventBatchPreviewRequest(HealthEventBatchCreate):
    user_id: int = Field(gt=0, description="Preview-only user identifier")


class HealthEventBatchPreviewResponse(BaseModel):
    batch_id: UUID
    received_count: int = Field(ge=0)
    normalized_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    events: list[HealthEventCreate]
    model_config = STRICT_CONFIG


class HealthEventBatchResponse(BaseModel):
    batch_id: UUID
    received_count: int = Field(ge=0)
    inserted_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    events: list[HealthEventResponse]
    model_config = STRICT_CONFIG


def reading_reference_time(reading: ReadingCreate | HealthEventCreate) -> datetime:
    if reading.temporal_type == TemporalType.INSTANT:
        assert reading.observed_at is not None
        return reading.observed_at
    assert reading.end_at is not None
    return reading.end_at


def reading_values(reading: ReadingCreate | HealthEventCreate) -> list[float]:
    if reading.temporal_type in {TemporalType.INSTANT, TemporalType.INTERVAL}:
        assert reading.value is not None
        return [reading.value]
    if reading.temporal_type == TemporalType.SERIES:
        return [sample.value for sample in reading.samples]
    assert reading.start_at is not None and reading.end_at is not None
    return [(reading.end_at - reading.start_at).total_seconds() / 60.0]


HealthEventBase = HealthEventCreate
