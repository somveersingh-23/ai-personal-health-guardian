"""Shared, non-diagnostic contracts for Member 2 sensor intelligence."""

from dataclasses import dataclass
from enum import Enum


class ValidationFlag(str, Enum):
    VALID = "valid"
    UNUSUAL_POSSIBLE = "unusual_possible"
    LOW_QUALITY = "low_quality"
    OUTSIDE_SUPPORTED_RANGE = "outside_supported_range"
    MALFORMED = "malformed"


class IntegrityStatus(str, Enum):
    VERIFIED = "verified"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class SignalQualityStatus(str, Enum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


class QualityStatus(str, Enum):
    """Compatibility tier used for aggregate feature usability, not diagnosis."""

    RELIABLE = "reliable"
    DEGRADED = "degraded"
    UNRELIABLE = "unreliable"
    UNKNOWN = "unknown"


class FreshnessStatus(str, Enum):
    REALTIME = "realtime"
    DELAYED = "delayed"
    HISTORICAL = "historical"


class TemporalType(str, Enum):
    INSTANT = "instant"
    INTERVAL = "interval"
    SERIES = "series"
    SESSION = "session"


class AggregationMethod(str, Enum):
    QUALITY_WEIGHTED_MEAN = "quality_weighted_mean"
    SUM = "sum"
    DURATION = "duration"
    LATEST = "latest"


class MetricType(str, Enum):
    HEART_RATE = "heart_rate"
    RESTING_HEART_RATE = "resting_heart_rate"
    HRV_RMSSD = "hrv_rmssd"
    SPO2 = "spo2"
    RESPIRATION_RATE = "respiration_rate"
    SKIN_TEMPERATURE = "skin_temperature"
    STEPS = "steps"
    SLEEP_DURATION = "sleep_duration"
    ACTIVE_CALORIES = "active_calories"


class SourceType(str, Enum):
    HEALTH_CONNECT = "health_connect"
    WEARABLE_BLUETOOTH = "wearable_bluetooth"
    CAMERA = "camera"
    MANUAL_ENTRY = "manual_entry"
    RESEARCH_DATASET = "research_dataset"
    SIMULATED = "simulated"


class PermissionState(str, Enum):
    GRANTED_FOREGROUND = "granted_foreground"
    GRANTED_BACKGROUND = "granted_background"
    DENIED = "denied"
    REVOKED = "revoked"
    UNAVAILABLE = "unavailable"


class RecordingMethod(str, Enum):
    UNKNOWN = "unknown"
    MANUAL_ENTRY = "manual_entry"
    AUTOMATICALLY_RECORDED = "automatically_recorded"
    ACTIVELY_RECORDED = "actively_recorded"
    SYNTHETIC = "synthetic"


class QualityDecision(str, Enum):
    """Pipeline usability decision; never a diagnosis or clinical interpretation."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class WearState(str, Enum):
    WORN = "worn"
    NOT_WORN = "not_worn"
    UNKNOWN = "unknown"


class MotionState(str, Enum):
    STILL = "still"
    MOVING = "moving"
    UNKNOWN = "unknown"


class DeviceSupportStatus(str, Enum):
    SUPPORTED = "supported"
    EXPERIMENTAL = "experimental"
    RESEARCH_ONLY = "research_only"
    BLOCKED = "blocked"
    DEPRECATED = "deprecated"


class CalibrationStatus(str, Enum):
    VALID = "valid"
    EXPIRED = "expired"
    NOT_REQUIRED = "not_required"
    UNVERIFIED = "unverified"


class ConsentStatus(str, Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ProcessingPurpose(str, Enum):
    SENSOR_INTELLIGENCE_WELLNESS = "sensor_intelligence_wellness"
    RESEARCH_VALIDATION = "research_validation"


class RetentionClass(str, Enum):
    TRANSIENT = "transient"
    NORMALIZED_OBSERVATION = "normalized_observation"
    DERIVED_EVIDENCE = "derived_evidence"
    AUDIT_METADATA = "audit_metadata"


class EventLifecycleStatus(str, Enum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    DELETED = "deleted"


class ClaimClass(str, Enum):
    ENGINEERING = "engineering"
    WELLNESS = "wellness"
    RESEARCH_ONLY = "research_only"
    CLINICAL_CANDIDATE = "clinical_candidate"
    PROHIBITED = "prohibited"


class EvidenceStatus(str, Enum):
    UNVALIDATED = "unvalidated"
    TECHNICALLY_VALIDATED = "technically_validated"
    EXTERNALLY_VALIDATED = "externally_validated"
    CLINICALLY_VALIDATED = "clinically_validated"


@dataclass(frozen=True, slots=True)
class MetricSpec:
    temporal_type: TemporalType
    units: frozenset[str]
    aggregation: AggregationMethod
    supported_range: tuple[float, float]


METRIC_SPECS: dict[MetricType, MetricSpec] = {
    MetricType.HEART_RATE: MetricSpec(
        TemporalType.SERIES, frozenset({"bpm"}), AggregationMethod.QUALITY_WEIGHTED_MEAN, (1.0, 300.0)
    ),
    MetricType.RESTING_HEART_RATE: MetricSpec(
        TemporalType.INSTANT, frozenset({"bpm"}), AggregationMethod.QUALITY_WEIGHTED_MEAN, (1.0, 300.0)
    ),
    MetricType.HRV_RMSSD: MetricSpec(
        TemporalType.INSTANT, frozenset({"ms"}), AggregationMethod.QUALITY_WEIGHTED_MEAN, (0.0, 1000.0)
    ),
    MetricType.SPO2: MetricSpec(
        TemporalType.INSTANT, frozenset({"%"}), AggregationMethod.QUALITY_WEIGHTED_MEAN, (1.0, 100.0)
    ),
    MetricType.RESPIRATION_RATE: MetricSpec(
        TemporalType.INSTANT,
        frozenset({"breaths/min"}),
        AggregationMethod.QUALITY_WEIGHTED_MEAN,
        (1.0, 120.0),
    ),
    MetricType.SKIN_TEMPERATURE: MetricSpec(
        TemporalType.SERIES,
        frozenset({"degC_delta", "degC"}),
        AggregationMethod.QUALITY_WEIGHTED_MEAN,
        (-30.0, 100.0),
    ),
    MetricType.STEPS: MetricSpec(
        TemporalType.INTERVAL, frozenset({"count"}), AggregationMethod.SUM, (1.0, 1_000_000.0)
    ),
    MetricType.SLEEP_DURATION: MetricSpec(
        TemporalType.SESSION, frozenset({"min"}), AggregationMethod.DURATION, (0.0, 1440.0)
    ),
    MetricType.ACTIVE_CALORIES: MetricSpec(
        TemporalType.INTERVAL, frozenset({"kcal"}), AggregationMethod.SUM, (0.0, 100_000.0)
    ),
}

METRIC_UNITS: dict[MetricType, frozenset[str]] = {
    metric: spec.units for metric, spec in METRIC_SPECS.items()
}

# UCUM is the canonical interchange representation. Existing connector-facing units
# remain accepted for backwards compatibility and are retained as source_unit.
CANONICAL_UCUM_UNITS: dict[MetricType, str] = {
    MetricType.HEART_RATE: "{beats}/min",
    MetricType.RESTING_HEART_RATE: "{beats}/min",
    MetricType.HRV_RMSSD: "ms",
    MetricType.SPO2: "%",
    MetricType.RESPIRATION_RATE: "{breaths}/min",
    MetricType.SKIN_TEMPERATURE: "Cel",
    MetricType.STEPS: "{count}",
    MetricType.SLEEP_DURATION: "min",
    MetricType.ACTIVE_CALORIES: "kcal",
}

# LOINC mappings are export hints, not proof that a source observation meets a
# clinical profile. Ambiguous metrics intentionally remain unmapped.
LOINC_CODES: dict[MetricType, str | None] = {
    MetricType.HEART_RATE: "8867-4",
    MetricType.RESTING_HEART_RATE: None,
    MetricType.HRV_RMSSD: None,
    MetricType.SPO2: "59408-5",
    MetricType.RESPIRATION_RATE: "9279-1",
    MetricType.SKIN_TEMPERATURE: None,
    MetricType.STEPS: "41950-7",
    MetricType.SLEEP_DURATION: "93832-4",
    MetricType.ACTIVE_CALORIES: None,
}


def derive_quality_status(score: float | None) -> QualityStatus:
    if score is None:
        return QualityStatus.UNKNOWN
    if score >= 0.80:
        return QualityStatus.RELIABLE
    if score >= 0.60:
        return QualityStatus.DEGRADED
    return QualityStatus.UNRELIABLE


def derive_integrity_status(score: float) -> IntegrityStatus:
    if score >= 0.80:
        return IntegrityStatus.VERIFIED
    if score >= 0.40:
        return IntegrityStatus.FLAGGED
    return IntegrityStatus.REJECTED


def derive_freshness_status(freshness_seconds: int) -> FreshnessStatus:
    if freshness_seconds <= 3600:
        return FreshnessStatus.REALTIME
    if freshness_seconds <= 86400:
        return FreshnessStatus.DELAYED
    return FreshnessStatus.HISTORICAL
