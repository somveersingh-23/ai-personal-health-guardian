"""Metric-aware window alignment and baseline-aware evidence fusion."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app.schemas.member2 import (
    METRIC_SPECS,
    AggregationMethod,
    EvidenceItem,
    FusedMetric,
    HealthEventCreate,
    MetricType,
    MultimodalEvidenceRequest,
    MultimodalEvidenceVector,
    MultimodalFeatureVector,
    QualityDecision,
    TemporalType,
    derive_quality_status,
)

SLEEPING_STAGES = {"sleeping", "light", "deep", "rem"}
SOURCE_DISAGREEMENT_TOLERANCE: dict[MetricType, float] = {
    MetricType.HEART_RATE: 20.0,
    MetricType.RESTING_HEART_RATE: 15.0,
    MetricType.HRV_RMSSD: 80.0,
    MetricType.SPO2: 4.0,
    MetricType.RESPIRATION_RATE: 5.0,
    MetricType.SKIN_TEMPERATURE: 1.5,
}


def _overlap_seconds(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> float:
    return max(0.0, (min(end, window_end) - max(start, window_start)).total_seconds())


def _event_in_window(event: HealthEventCreate, start: datetime, end: datetime) -> bool:
    if event.temporal_type == TemporalType.INSTANT:
        return event.observed_at is not None and start <= event.observed_at < end
    return (
        event.start_at is not None
        and event.end_at is not None
        and event.start_at < end
        and event.end_at > start
    )


def _quality(event: HealthEventCreate) -> float:
    vector = event.quality_vector
    if vector.decision == QualityDecision.REJECTED:
        return 0.0
    components = [
        vector.record_integrity_score,
        vector.provenance_confidence,
        vector.freshness_score,
    ]
    optional = (
        vector.signal_quality_score,
        vector.coverage_score,
        vector.wear_confidence,
        None if vector.motion_artifact_score is None else 1.0 - vector.motion_artifact_score,
        vector.calibration_confidence,
        vector.device_validation_confidence,
    )
    components.extend(value for value in optional if value is not None)
    if any(value <= 0 for value in components):
        return 0.001
    harmonic_mean = len(components) / sum(1.0 / value for value in components)
    if vector.decision == QualityDecision.UNKNOWN:
        harmonic_mean *= 0.75
    return max(0.0, min(1.0, harmonic_mean))


def _missing_quality_dimensions(events: list[HealthEventCreate]) -> list[str]:
    dimensions = {
        "signal_quality": lambda event: event.quality_vector.signal_quality_score,
        "coverage": lambda event: event.quality_vector.coverage_score,
        "wear": lambda event: event.quality_vector.wear_confidence,
        "motion": lambda event: event.quality_vector.motion_artifact_score,
        "calibration": lambda event: event.quality_vector.calibration_confidence,
        "device_validation": lambda event: event.quality_vector.device_validation_confidence,
    }
    return sorted(
        name for name, getter in dimensions.items() if all(getter(event) is None for event in events)
    )


def _source_contradiction(metric: MetricType, events: list[HealthEventCreate]) -> str | None:
    tolerance = SOURCE_DISAGREEMENT_TOLERANCE.get(metric)
    if tolerance is None:
        return None
    values_by_source: dict[tuple[str, str], list[float]] = defaultdict(list)
    for event in events:
        if event.value is not None:
            values_by_source[_source_key(event)].append(event.value)
        else:
            values_by_source[_source_key(event)].extend(sample.value for sample in event.samples)
    means = [sum(values) / len(values) for values in values_by_source.values() if values]
    if len(means) >= 2 and max(means) - min(means) > tolerance:
        return f"{metric.value}:source_disagreement"
    return None


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> float:
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    merged: list[tuple[datetime, datetime]] = [ordered[0]]
    for start, end in ordered[1:]:
        previous_start, previous_end = merged[-1]
        if start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return sum((end - start).total_seconds() for start, end in merged)


def _coverage(events: list[HealthEventCreate], start: datetime, end: datetime) -> float:
    intervals = [
        (max(event.start_at, start), min(event.end_at, end))
        for event in events
        if event.start_at is not None and event.end_at is not None and _event_in_window(event, start, end)
    ]
    return _merge_intervals(intervals)


def _source_key(event: HealthEventCreate) -> tuple[str, str]:
    return event.data_origin_package, event.device_id or "unknown-device"


def _select_cumulative_source(
    events: list[HealthEventCreate], start: datetime, end: datetime
) -> list[HealthEventCreate]:
    """Avoid double-counting mirrored cumulative records from multiple devices/apps."""

    grouped: dict[tuple[str, str], list[HealthEventCreate]] = defaultdict(list)
    for event in events:
        grouped[_source_key(event)].append(event)
    return max(
        grouped.values(),
        key=lambda group: (_coverage(group, start, end), sum(_quality(item) for item in group) / len(group)),
    )


def _aggregate_mean(
    metric: MetricType,
    candidates: list[HealthEventCreate],
    start: datetime,
    end: datetime,
) -> tuple[float, int, float, list[HealthEventCreate]]:
    values: list[tuple[float, float]] = []
    contributors: list[HealthEventCreate] = []
    for event in candidates:
        weight = _quality(event)
        if event.temporal_type == TemporalType.INSTANT and event.observed_at is not None:
            if start <= event.observed_at < end and event.value is not None:
                values.append((event.value, weight))
                contributors.append(event)
        elif event.temporal_type == TemporalType.SERIES:
            samples = [sample for sample in event.samples if start <= sample.observed_at < end]
            if samples:
                values.extend((sample.value, weight) for sample in samples)
                contributors.append(event)
    if not values:
        raise ValueError(f"no usable values for {metric.value}")
    weighted_mean = sum(value * weight for value, weight in values) / sum(weight for _, weight in values)
    return weighted_mean, len(values), _coverage(contributors, start, end), contributors


def _aggregate_sum(
    candidates: list[HealthEventCreate], start: datetime, end: datetime
) -> tuple[float, int, float, list[HealthEventCreate]]:
    selected = _select_cumulative_source(candidates, start, end)
    total = 0.0
    for event in selected:
        assert event.start_at is not None and event.end_at is not None and event.value is not None
        record_seconds = (event.end_at - event.start_at).total_seconds()
        overlap = _overlap_seconds(event.start_at, event.end_at, start, end)
        if record_seconds > 0:
            total += event.value * (overlap / record_seconds)
    return total, len(selected), _coverage(selected, start, end), selected


def _aggregate_sleep_duration(
    candidates: list[HealthEventCreate], start: datetime, end: datetime
) -> tuple[float, int, float, list[HealthEventCreate]]:
    selected = _select_cumulative_source(candidates, start, end)
    intervals: list[tuple[datetime, datetime]] = []
    for event in selected:
        usable_stages = [stage for stage in event.stages if stage.stage in SLEEPING_STAGES]
        if usable_stages:
            intervals.extend(
                (max(stage.start_at, start), min(stage.end_at, end))
                for stage in usable_stages
                if stage.start_at < end and stage.end_at > start
            )
        else:
            assert event.start_at is not None and event.end_at is not None
            intervals.append((max(event.start_at, start), min(event.end_at, end)))
    seconds = _merge_intervals(intervals)
    return seconds / 60.0, len(intervals), seconds, selected


def fuse_events(
    events: list[HealthEventCreate],
    requested_metrics: list[MetricType],
    window_start: datetime,
    window_end: datetime,
    min_integrity_score: float = 0.50,
    min_composite_quality: float = 0.35,
    min_available_metrics: int = 1,
) -> MultimodalFeatureVector:
    """Align and aggregate records with metric-specific semantics; never infer disease."""

    if not events:
        raise ValueError("at least one event is required")
    if window_start.tzinfo is None or window_end.tzinfo is None:
        raise ValueError("window timestamps must include UTC offsets")
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")
    user_ids = {event.user_id for event in events}
    if len(user_ids) != 1:
        raise ValueError("all events must belong to one user")
    if len(requested_metrics) != len(set(requested_metrics)):
        raise ValueError("requested_metrics must be unique")

    features: list[FusedMetric] = []
    missing: list[MetricType] = []
    used_events: list[HealthEventCreate] = []
    contradictions: list[str] = []
    for metric in requested_metrics:
        candidates = [
            event
            for event in events
            if event.metric == metric
            and event.record_integrity_score >= min_integrity_score
            and event.quality_vector.decision != QualityDecision.REJECTED
            and _event_in_window(event, window_start, window_end)
        ]
        if not candidates:
            missing.append(metric)
            continue
        contradiction = _source_contradiction(metric, candidates)
        if contradiction:
            contradictions.append(contradiction)
        method = METRIC_SPECS[metric].aggregation
        if method == AggregationMethod.QUALITY_WEIGHTED_MEAN:
            value, sample_count, coverage, selected = _aggregate_mean(
                metric, candidates, window_start, window_end
            )
        elif method == AggregationMethod.SUM:
            value, sample_count, coverage, selected = _aggregate_sum(candidates, window_start, window_end)
        elif method == AggregationMethod.DURATION:
            value, sample_count, coverage, selected = _aggregate_sleep_duration(
                candidates, window_start, window_end
            )
        else:
            raise ValueError(f"unsupported aggregation method: {method.value}")
        used_events.extend(selected)
        quality = sum(_quality(event) for event in selected) / len(selected)
        features.append(
            FusedMetric(
                metric=metric,
                value=value,
                unit=selected[0].unit,
                aggregation_method=method,
                sample_count=sample_count,
                source_record_count=len(selected),
                coverage_seconds=coverage,
                quality_weight=quality,
                quality_decision=(
                    QualityDecision.ACCEPTED
                    if all(
                        event.quality_vector.decision == QualityDecision.ACCEPTED
                        for event in selected
                    )
                    else QualityDecision.UNKNOWN
                ),
                selected_source_keys=[
                    f"{package}:{device}"
                    for package, device in sorted({_source_key(item) for item in selected})
                ],
                missing_quality_dimensions=_missing_quality_dimensions(selected),
                source_event_ids=[str(event.event_id) for event in selected],
            )
        )

    composite = (
        sum(feature.quality_weight for feature in features) / len(features) if features else 0.0
    )
    abstention_reasons: list[str] = []
    if not features:
        abstention_reasons.append("no_eligible_records")
    if len(features) < min_available_metrics:
        abstention_reasons.append("insufficient_available_metrics")
    if composite < min_composite_quality:
        abstention_reasons.append("composite_quality_below_threshold")
    unique_used = {str(event.event_id): event for event in used_events}.values()
    return MultimodalFeatureVector(
        user_id=events[0].user_id,
        window_start=window_start,
        window_end=window_end,
        features=features,
        missing_metrics=missing,
        composite_quality_score=composite,
        composite_quality_status=derive_quality_status(composite),
        abstained=bool(abstention_reasons),
        abstention_reasons=abstention_reasons,
        contradictions=contradictions,
        provenance={
            "event_count": len(list(unique_used)),
            "sources": sorted({event.source.value for event in used_events}),
            "devices": sorted({event.device_id for event in used_events if event.device_id}),
            "data_origin_packages": sorted({event.data_origin_package for event in used_events}),
            "algorithm": "quality-aware-late-fusion-v3",
            "cumulative_source_policy": "highest-coverage-source",
            "non_diagnostic": True,
        },
    )


def fuse_baseline_evidence(request: MultimodalEvidenceRequest) -> MultimodalEvidenceVector:
    """Combine Member 1 standardized deviations into evidence strength, not medical risk."""

    if request.vector.abstained:
        return MultimodalEvidenceVector(
            user_id=request.vector.user_id,
            window_start=request.vector.window_start,
            window_end=request.vector.window_end,
            evidence=[],
            combined_evidence_strength=0.0,
            missing_baselines=[item.metric for item in request.vector.features],
            abstained=True,
            abstention_reasons=["input_feature_vector_abstained"],
        )
    features = {item.metric: item for item in request.vector.features}
    deviations = {item.metric: item for item in request.baseline_deviations}
    evidence: list[EvidenceItem] = []
    missing: list[MetricType] = []
    for metric, feature in features.items():
        deviation = deviations.get(metric)
        if deviation is None or deviation.status == "unknown":
            missing.append(metric)
            continue
        direction = {
            "below_normal": "below",
            "above_normal": "above",
            "normal": "normal",
        }[deviation.status]
        magnitude = min(abs(deviation.deviation_score) / 3.0, 1.0)
        evidence.append(
            EvidenceItem(
                metric=metric,
                direction=direction,
                standardized_deviation=deviation.deviation_score,
                evidence_weight=magnitude * feature.quality_weight,
                quality_weight=feature.quality_weight,
            )
        )
    strength = sum(item.evidence_weight for item in evidence) / len(evidence) if evidence else 0.0
    return MultimodalEvidenceVector(
        user_id=request.vector.user_id,
        window_start=request.vector.window_start,
        window_end=request.vector.window_end,
        evidence=evidence,
        combined_evidence_strength=strength,
        missing_baselines=missing,
        abstained=not evidence,
        abstention_reasons=[] if evidence else ["no_usable_baseline_evidence"],
    )
