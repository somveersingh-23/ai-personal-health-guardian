"""Adversarial unit tests for typed records, quality, and aggregation semantics."""

from datetime import timedelta
from math import sin

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.member2 import (
    CameraFrameQualityRequest,
    HealthEventBatchPreviewRequest,
    InstantReadingCreate,
    IntervalReadingCreate,
    MetricType,
    MultimodalEvidenceRequest,
    ReadingCreate,
    RecordingMethod,
    SeriesReadingCreate,
    SeriesSample,
    SessionReadingCreate,
    SessionStage,
    SignalQualityStatus,
    SourceType,
    WaveformQualityAssessmentRequest,
)
from app.services.sensors import (
    assess_camera_frame_quality,
    assess_record_integrity,
    assess_waveform_quality,
    fuse_baseline_evidence,
    fuse_events,
    generate_health_feed,
    normalize_batch_readings,
    normalize_reading,
)
from tests.member2.conftest import NOW, hc_common


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        InstantReadingCreate(
            temporal_type="instant",
            metric="spo2",
            unit="%",
            observed_at=NOW,
            value=98,
            source="manual_entry",
            recording_method="manual_entry",
            unexpected_admin=True,
        )


def test_metadata_size_and_shape_are_bounded():
    with pytest.raises(ValidationError, match="8192"):
        InstantReadingCreate(
            metric="spo2",
            unit="%",
            observed_at=NOW,
            value=98,
            source="manual_entry",
            recording_method="manual_entry",
            metadata={"blob": "x" * 9000},
        )

    nested: object = "leaf"
    for _ in range(10):
        nested = {"next": nested}
    with pytest.raises(ValidationError, match="nesting"):
        InstantReadingCreate(
            metric="spo2",
            unit="%",
            observed_at=NOW,
            value=98,
            source="manual_entry",
            recording_method="manual_entry",
            metadata={"nested": nested},
        )


def test_numeric_strings_and_booleans_are_not_coerced_to_measurements():
    for untrusted_value in ("98", True):
        with pytest.raises(ValidationError, match="finite"):
            InstantReadingCreate(
                metric="spo2",
                unit="%",
                observed_at=NOW,
                value=untrusted_value,
                source="manual_entry",
                recording_method="manual_entry",
            )


def test_metric_temporal_shape_is_enforced():
    with pytest.raises(ValidationError, match="requires temporal_type='interval'"):
        InstantReadingCreate(
            metric="steps",
            unit="count",
            observed_at=NOW,
            value=100,
            source="manual_entry",
            recording_method="manual_entry",
        )


def test_health_connect_requires_full_identity():
    with pytest.raises(ValidationError, match="complete source identity"):
        SeriesReadingCreate(
            metric="heart_rate",
            unit="bpm",
            start_at=NOW,
            end_at=NOW + timedelta(minutes=1),
            samples=[SeriesSample(observed_at=NOW, value=72)],
            source="health_connect",
            recording_method="automatically_recorded",
        )


def test_research_dataset_requires_explicit_offline_identity():
    with pytest.raises(ValidationError, match="complete offline identity"):
        InstantReadingCreate(
            metric="spo2",
            unit="%",
            observed_at=NOW,
            value=98,
            source="research_dataset",
            recording_method="automatically_recorded",
        )

    reading = InstantReadingCreate(
        metric="spo2",
        unit="%",
        observed_at=NOW,
        value=98,
        source="research_dataset",
        data_origin_package="research.bidmc",
        source_record_type="BIDMCReferenceSpO2",
        source_record_id="bidmc-01-spo2-0",
        device_id="bidmc:01",
        recording_method="automatically_recorded",
        permission_state="unavailable",
    )
    assert reading.source == SourceType.RESEARCH_DATASET


def test_spo2_zero_is_flagged_and_not_called_signal_quality():
    reading = InstantReadingCreate(
        metric="spo2",
        unit="%",
        observed_at=NOW,
        value=0,
        source="manual_entry",
        recording_method="manual_entry",
    )
    result = assess_record_integrity(reading, NOW)
    assert result.record_integrity_status.value == "flagged"
    assert result.signal_quality_score is None
    assert result.signal_quality_status == SignalQualityStatus.UNKNOWN
    assert result.validation_flag.value == "outside_supported_range"


def test_future_clock_skew_is_rejected():
    reading = InstantReadingCreate(
        metric="spo2",
        unit="%",
        observed_at=NOW + timedelta(minutes=2),
        value=98,
        source="manual_entry",
        recording_method="manual_entry",
    )
    with pytest.raises(ValueError, match="clock-skew"):
        assess_record_integrity(reading, NOW)


def test_waveform_sqi_abstains_on_flatline_and_accepts_dynamic_fixture():
    flat = assess_waveform_quality(WaveformQualityAssessmentRequest(samples=[1.0] * 64, sampling_rate_hz=64))
    dynamic = assess_waveform_quality(
        WaveformQualityAssessmentRequest(
            samples=[sin(index / 5) for index in range(128)],
            sampling_rate_hz=64,
        )
    )
    assert flat.usable is False
    assert flat.signal_quality_status.value == "poor"
    assert dynamic.usable is True
    assert dynamic.non_diagnostic is True


def test_camera_quality_rejects_blur_motion_and_bad_exposure():
    result = assess_camera_frame_quality(
        CameraFrameQualityRequest(
            mean_luminance=20,
            luminance_stddev=5,
            blur_variance=20,
            motion_score=0.8,
            clipped_dark_fraction=0.5,
            clipped_bright_fraction=0,
        )
    )
    assert result.accepted is False
    assert {"underexposed", "blurred", "excessive motion"}.issubset(result.reasons)
    assert result.non_diagnostic is True


def test_steps_are_summed_not_averaged():
    records = [
        IntervalReadingCreate(
            **hc_common("StepsRecord", f"steps-{index}"),
            metric="steps",
            unit="count",
            start_at=NOW + timedelta(hours=index),
            end_at=NOW + timedelta(hours=index + 1),
            value=value,
        )
        for index, value in enumerate((100.0, 200.0))
    ]
    events = [normalize_reading(record, 1, NOW + timedelta(hours=3)) for record in records]
    vector = fuse_events(events, [MetricType.STEPS], NOW, NOW + timedelta(hours=2))
    assert vector.features[0].value == 300
    assert vector.features[0].aggregation_method.value == "sum"


def test_cumulative_metric_chooses_one_source_to_avoid_double_counting():
    records = []
    for package, value in (("com.watch.a", 100.0), ("com.watch.b", 110.0)):
        common = hc_common("StepsRecord", package)
        common["data_origin_package"] = package
        records.append(
            IntervalReadingCreate(
                **common,
                metric="steps",
                unit="count",
                start_at=NOW,
                end_at=NOW + timedelta(hours=1),
                value=value,
            )
        )
    events = [normalize_reading(record, 1, NOW + timedelta(hours=2)) for record in records]
    vector = fuse_events(events, [MetricType.STEPS], NOW, NOW + timedelta(hours=1))
    assert vector.features[0].value in {100.0, 110.0}
    assert vector.features[0].source_record_count == 1


def test_sleep_duration_excludes_awake_stage():
    record = SessionReadingCreate(
        **hc_common("SleepSessionRecord", "sleep-1"),
        metric="sleep_duration",
        unit="min",
        start_at=NOW,
        end_at=NOW + timedelta(hours=8),
        stages=[
            SessionStage(start_at=NOW, end_at=NOW + timedelta(minutes=30), stage="awake_in_bed"),
            SessionStage(
                start_at=NOW + timedelta(minutes=30),
                end_at=NOW + timedelta(hours=8),
                stage="sleeping",
            ),
        ],
    )
    event = normalize_reading(record, 1, NOW + timedelta(hours=9))
    vector = fuse_events([event], [MetricType.SLEEP_DURATION], NOW, NOW + timedelta(hours=8))
    assert vector.features[0].value == 450


def test_series_mean_uses_samples():
    record = SeriesReadingCreate(
        **hc_common("HeartRateRecord", "hr-1"),
        metric="heart_rate",
        unit="bpm",
        start_at=NOW,
        end_at=NOW + timedelta(minutes=2),
        samples=[
            SeriesSample(observed_at=NOW, value=70),
            SeriesSample(observed_at=NOW + timedelta(minutes=1), value=80),
        ],
    )
    event = normalize_reading(record, 1, NOW + timedelta(minutes=3))
    vector = fuse_events([event], [MetricType.HEART_RATE], NOW, NOW + timedelta(minutes=2))
    assert vector.features[0].value == 75
    assert vector.features[0].sample_count == 2


def test_series_provenance_contains_only_records_with_contributing_samples():
    outside = SeriesReadingCreate(
        **hc_common("HeartRateRecord", "hr-outside"),
        metric="heart_rate",
        unit="bpm",
        start_at=NOW,
        end_at=NOW + timedelta(seconds=90),
        samples=[SeriesSample(observed_at=NOW + timedelta(seconds=30), value=60)],
    )
    inside = SeriesReadingCreate(
        **hc_common("HeartRateRecord", "hr-inside"),
        metric="heart_rate",
        unit="bpm",
        start_at=NOW + timedelta(minutes=1),
        end_at=NOW + timedelta(minutes=3),
        samples=[SeriesSample(observed_at=NOW + timedelta(seconds=90), value=75)],
    )
    events = [normalize_reading(item, 1, NOW + timedelta(minutes=4)) for item in (outside, inside)]
    vector = fuse_events(
        events,
        [MetricType.HEART_RATE],
        NOW + timedelta(minutes=1),
        NOW + timedelta(minutes=2),
    )
    assert vector.features[0].value == 75
    assert vector.features[0].source_record_count == 1
    assert vector.features[0].source_event_ids == [str(events[1].event_id)]
    assert vector.provenance["event_count"] == 1


def test_batch_is_atomic_contract_without_dead_rejected_count():
    reading = InstantReadingCreate(
        metric="spo2",
        unit="%",
        observed_at=NOW,
        value=98,
        source=SourceType.SIMULATED,
        recording_method=RecordingMethod.SYNTHETIC,
    )
    result = normalize_batch_readings(HealthEventBatchPreviewRequest(user_id=1, events=[reading]), NOW)
    assert result.normalized_count == 1
    assert "rejected_count" not in result.model_dump()


def test_simulated_baseline_evidence_abstains_and_is_non_diagnostic():
    feed = generate_health_feed(1, NOW, hours=1, seed=4)
    events = [normalize_reading(record, 1, NOW + timedelta(hours=2)) for record in feed]
    vector = fuse_events(events, [MetricType.HEART_RATE, MetricType.STEPS], NOW, NOW + timedelta(hours=1))
    request = MultimodalEvidenceRequest(
        vector=vector,
        baseline_deviations=[
            {"metric": "heart_rate", "deviation_score": 2.0, "status": "above_normal"},
            {"metric": "steps", "deviation_score": -1.5, "status": "below_normal"},
        ],
    )
    result = fuse_baseline_evidence(request)
    assert result.non_diagnostic is True
    assert vector.abstained is True
    assert result.abstained is True
    assert result.evidence == []
    assert result.combined_evidence_strength == 0


def test_simulator_is_typed_deterministic_and_labelled():
    first = generate_health_feed(1, NOW, hours=2, seed=9)
    second = generate_health_feed(1, NOW, hours=2, seed=9)
    assert [item.model_dump() for item in first] == [item.model_dump() for item in second]
    assert {item.temporal_type.value for item in first} == {"instant", "interval", "series", "session"}
    assert all(item.source == SourceType.SIMULATED for item in first)
    assert all(item.recording_method == RecordingMethod.SYNTHETIC for item in first)


def test_discriminated_union_rejects_wrong_shape():
    adapter = TypeAdapter(ReadingCreate)
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "temporal_type": "interval",
                "metric": "steps",
                "unit": "count",
                "source": "manual_entry",
                "recording_method": "manual_entry",
                "observed_at": NOW.isoformat(),
                "value": 10,
            }
        )
