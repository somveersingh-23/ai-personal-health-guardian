"""Window alignment and baseline-aware multimodal evidence contracts."""

from datetime import datetime
from math import isfinite
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.member2.common import (
    AggregationMethod,
    MetricType,
    QualityDecision,
    QualityStatus,
)
from app.schemas.member2.health_event import STRICT_CONFIG, HealthEventCreate


class FusedMetric(BaseModel):
    metric: MetricType
    value: float
    unit: str
    aggregation_method: AggregationMethod
    sample_count: int = Field(ge=1)
    source_record_count: int = Field(ge=1)
    coverage_seconds: float = Field(ge=0.0)
    quality_weight: float = Field(ge=0.0, le=1.0)
    quality_decision: QualityDecision
    selected_source_keys: list[str] = Field(min_length=1, max_length=100)
    missing_quality_dimensions: list[str] = Field(default_factory=list, max_length=16)
    source_event_ids: list[str] = Field(min_length=1, max_length=1000)
    model_config = STRICT_CONFIG


class MultimodalFeatureVector(BaseModel):
    schema_version: Literal["3.0.0"] = "3.0.0"
    user_id: int = Field(gt=0)
    window_start: datetime
    window_end: datetime
    features: list[FusedMetric] = Field(default_factory=list, max_length=50)
    missing_metrics: list[MetricType] = Field(default_factory=list)
    composite_quality_score: float = Field(ge=0.0, le=1.0)
    composite_quality_status: QualityStatus
    abstained: bool = False
    abstention_reasons: list[str] = Field(default_factory=list, max_length=32)
    contradictions: list[str] = Field(default_factory=list, max_length=32)
    algorithm_version: Literal["quality-aware-late-fusion-v3"] = "quality-aware-late-fusion-v3"
    provenance: dict[str, object] = Field(default_factory=dict)
    model_config = STRICT_CONFIG

    @model_validator(mode="after")
    def valid_window(self) -> "MultimodalFeatureVector":
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("window timestamps must include UTC offsets")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


class MultimodalFusionRequest(BaseModel):
    window_start: datetime
    window_end: datetime
    requested_metrics: list[MetricType] = Field(min_length=1, max_length=20)
    minimum_integrity_score: float = Field(default=0.50, ge=0.0, le=1.0)
    minimum_composite_quality: float = Field(default=0.35, ge=0.0, le=1.0)
    minimum_available_metrics: int = Field(default=1, ge=1, le=20)
    model_config = STRICT_CONFIG

    @model_validator(mode="after")
    def validate_request(self) -> "MultimodalFusionRequest":
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("window timestamps must include UTC offsets")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if len(set(self.requested_metrics)) != len(self.requested_metrics):
            raise ValueError("requested_metrics must be unique")
        return self


class MultimodalFusionPreviewRequest(MultimodalFusionRequest):
    user_id: int = Field(gt=0)
    events: list[HealthEventCreate] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def user_isolation(self) -> "MultimodalFusionPreviewRequest":
        if any(event.user_id != self.user_id for event in self.events):
            raise ValueError("every event user_id must match the preview user_id")
        return self


class MultimodalFusionResponse(BaseModel):
    vector: MultimodalFeatureVector
    model_config = STRICT_CONFIG


class BaselineDeviation(BaseModel):
    metric: MetricType
    deviation_score: float = Field(description="Member 1 standardized deviation; not medical risk")
    status: Literal["normal", "below_normal", "above_normal", "unknown"]
    model_config = STRICT_CONFIG

    @field_validator("deviation_score")
    @classmethod
    def finite_score(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("deviation_score must be finite")
        return value


class EvidenceItem(BaseModel):
    metric: MetricType
    direction: Literal["below", "normal", "above", "unknown"]
    standardized_deviation: float
    evidence_weight: float = Field(ge=0.0, le=1.0)
    quality_weight: float = Field(ge=0.0, le=1.0)
    model_config = STRICT_CONFIG


class MultimodalEvidenceRequest(BaseModel):
    vector: MultimodalFeatureVector
    baseline_deviations: list[BaselineDeviation] = Field(min_length=1, max_length=50)
    model_config = STRICT_CONFIG

    @model_validator(mode="after")
    def unique_deviations(self) -> "MultimodalEvidenceRequest":
        metrics = [item.metric for item in self.baseline_deviations]
        if len(metrics) != len(set(metrics)):
            raise ValueError("baseline_deviations must contain unique metrics")
        return self


class MultimodalEvidenceVector(BaseModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    user_id: int = Field(gt=0)
    window_start: datetime
    window_end: datetime
    evidence: list[EvidenceItem]
    combined_evidence_strength: float = Field(ge=0.0, le=1.0)
    missing_baselines: list[MetricType]
    abstained: bool = False
    abstention_reasons: list[str] = Field(default_factory=list, max_length=32)
    non_diagnostic: Literal[True] = True
    model_config = STRICT_CONFIG


AlignedHealthFeatures = MultimodalFeatureVector
