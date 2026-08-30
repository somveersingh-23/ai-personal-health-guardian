"""Auditable record-integrity and non-clinical acquisition-quality policies."""

from __future__ import annotations

from datetime import UTC, datetime
from math import sqrt
from statistics import fmean, pstdev

from app.schemas.member2 import (
    METRIC_SPECS,
    CameraFrameQualityRequest,
    CameraFrameQualityResponse,
    IntegrityStatus,
    MotionState,
    QualityAssessmentResponse,
    QualityDecision,
    QualityVector,
    ReadingCreate,
    RecordingMethod,
    SignalQualityStatus,
    ValidationFlag,
    WaveformQualityAssessmentRequest,
    WaveformQualityResponse,
    WearState,
    derive_freshness_status,
    derive_integrity_status,
    reading_reference_time,
    reading_values,
)

MAX_CLOCK_SKEW_SECONDS = 60
INTEGRITY_POLICY_VERSION = "record-integrity-v1"


def _provenance_confidence(reading: ReadingCreate) -> float:
    if reading.source.value == "simulated":
        return 0.0
    if reading.source.value == "manual_entry":
        return 0.45
    if reading.source.value == "research_dataset":
        return 0.85
    score = 0.55
    if reading.data_origin_package and reading.source_record_type and reading.source_record_id:
        score += 0.20
    if reading.recording_method != RecordingMethod.UNKNOWN:
        score += 0.10
    if reading.device_type:
        score += 0.10
    return min(score, 1.0)


def _coverage_score(reading: ReadingCreate) -> float | None:
    if reading.temporal_type.value == "instant":
        return None
    if reading.temporal_type.value == "series":
        duration = (reading.end_at - reading.start_at).total_seconds()  # type: ignore[operator]
        if reading.sampling_rate_hz is None or duration <= 0:
            return None
        expected = max(1.0, duration * reading.sampling_rate_hz)
        return min(len(reading.samples) / expected, 1.0)  # type: ignore[attr-defined]
    if reading.temporal_type.value == "session":
        duration = (reading.end_at - reading.start_at).total_seconds()  # type: ignore[operator]
        if duration <= 0 or not reading.stages:  # type: ignore[attr-defined]
            return None
        covered = sum(
            (stage.end_at - stage.start_at).total_seconds() for stage in reading.stages  # type: ignore[attr-defined]
        )
        return min(covered / duration, 1.0)
    return 1.0


def _freshness_score(freshness_seconds: int) -> float:
    if freshness_seconds <= 3600:
        return 1.0
    if freshness_seconds <= 86400:
        return 0.75
    if freshness_seconds <= 7 * 86400:
        return 0.50
    return 0.25


def _quality_vector(
    reading: ReadingCreate,
    *,
    integrity_score: float,
    integrity_status: IntegrityStatus,
    freshness_seconds: int,
) -> QualityVector:
    provenance = _provenance_confidence(reading)
    reasons: list[str] = []
    if integrity_status == IntegrityStatus.REJECTED:
        decision = QualityDecision.REJECTED
        reasons.append("record_integrity_rejected")
    elif integrity_status == IntegrityStatus.FLAGGED or provenance < 0.60:
        decision = QualityDecision.UNKNOWN
        reasons.append("insufficient_trust_evidence")
    else:
        decision = QualityDecision.ACCEPTED
    if reading.wear_state == WearState.UNKNOWN:
        reasons.append("wear_state_unknown")
    if reading.motion_state == MotionState.UNKNOWN:
        reasons.append("motion_state_unknown")
    reasons.extend(("signal_quality_unavailable", "device_validation_unavailable"))
    return QualityVector(
        decision=decision,
        record_integrity_score=integrity_score,
        signal_quality_score=None,
        provenance_confidence=provenance,
        freshness_score=_freshness_score(freshness_seconds),
        coverage_score=_coverage_score(reading),
        wear_confidence=(
            1.0
            if reading.wear_state == WearState.WORN
            else 0.0
            if reading.wear_state == WearState.NOT_WORN
            else None
        ),
        motion_artifact_score=reading.motion_artifact_score,
        calibration_confidence=None,
        device_validation_confidence=None,
        reason_codes=reasons,
    )


def assess_record_integrity(
    reading: ReadingCreate,
    received_at: datetime,
) -> QualityAssessmentResponse:
    """Assess record usability without pretending scalar plausibility is signal quality."""

    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError("received_at must include a UTC offset")
    reference_time = reading_reference_time(reading).astimezone(UTC)
    received_utc = received_at.astimezone(UTC)
    future_skew = (reference_time - received_utc).total_seconds()
    if future_skew > MAX_CLOCK_SKEW_SECONDS:
        raise ValueError(f"record time exceeds {MAX_CLOCK_SKEW_SECONDS}s future clock-skew tolerance")

    freshness_seconds = max(0, int((received_utc - reference_time).total_seconds()))
    freshness_status = derive_freshness_status(freshness_seconds)
    score = 1.0
    reasons: list[str] = []

    if reading.recording_method == RecordingMethod.UNKNOWN:
        score -= 0.10
        reasons.append("recording method is unknown")
    if (
        reading.recording_method
        in {RecordingMethod.AUTOMATICALLY_RECORDED, RecordingMethod.ACTIVELY_RECORDED}
        and not reading.device_type
    ):
        score -= 0.15
        reasons.append("recorded sensor data is missing device type")

    low, high = METRIC_SPECS[reading.metric].supported_range
    outside_count = sum(not low <= value <= high for value in reading_values(reading))
    validation_flag = ValidationFlag.VALID
    if outside_count:
        score -= 0.50
        validation_flag = ValidationFlag.OUTSIDE_SUPPORTED_RANGE
        reasons.append(
            f"{outside_count} value(s) outside connector guardrail [{low}, {high}]; "
            "this is not a diagnostic reference range"
        )

    score = max(0.0, min(1.0, score))
    status = derive_integrity_status(score)
    if status == IntegrityStatus.REJECTED and validation_flag == ValidationFlag.VALID:
        validation_flag = ValidationFlag.MALFORMED

    return QualityAssessmentResponse(
        record_integrity_score=score,
        record_integrity_status=status,
        signal_quality_score=None,
        signal_quality_status=SignalQualityStatus.UNKNOWN,
        freshness_status=freshness_status,
        data_freshness_seconds=freshness_seconds,
        validation_flag=validation_flag,
        validation_reason="; ".join(reasons) or None,
        remeasure_recommended=status != IntegrityStatus.VERIFIED,
        policy_version=INTEGRITY_POLICY_VERSION,
        assessment_details={
            "source": reading.source.value,
            "temporal_type": reading.temporal_type.value,
            "recording_method": reading.recording_method.value,
            "outside_guardrail_count": outside_count,
            "signal_quality_available": False,
        },
        quality_vector=_quality_vector(
            reading,
            integrity_score=score,
            integrity_status=status,
            freshness_seconds=freshness_seconds,
        ),
    )


def _correlation(first: list[float], second: list[float]) -> float | None:
    first_mean = fmean(first)
    second_mean = fmean(second)
    first_var = sum((value - first_mean) ** 2 for value in first)
    second_var = sum((value - second_mean) ** 2 for value in second)
    if first_var == 0 or second_var == 0:
        return None
    covariance = sum((a - first_mean) * (b - second_mean) for a, b in zip(first, second, strict=False))
    return max(-1.0, min(1.0, covariance / sqrt(first_var * second_var)))


def assess_waveform_quality(request: WaveformQualityAssessmentRequest) -> WaveformQualityResponse:
    """Transparent research SQI; it abstains from physiological interpretation."""

    samples = request.samples
    signal_range = max(samples) - min(samples)
    epsilon = max(signal_range * 1e-6, 1e-12)
    flatline_fraction = sum(
        abs(a - b) <= epsilon for a, b in zip(samples, samples[1:], strict=False)
    ) / (len(samples) - 1)
    min_value, max_value = min(samples), max(samples)
    clipping_fraction = sum(
        abs(value - min_value) <= epsilon or abs(value - max_value) <= epsilon for value in samples
    ) / len(samples)
    motion_correlation = (
        _correlation(samples, request.motion_reference) if request.motion_reference is not None else None
    )

    score = 1.0
    if signal_range <= epsilon or pstdev(samples) <= epsilon:
        score = 0.0
    score -= min(0.60, clipping_fraction * 2.0)
    score -= min(0.60, flatline_fraction * 2.0)
    if motion_correlation is not None:
        score -= min(0.50, abs(motion_correlation) * 0.50)
    score = max(0.0, min(1.0, score))

    if score >= 0.80:
        status = SignalQualityStatus.GOOD
    elif score >= 0.55:
        status = SignalQualityStatus.FAIR
    else:
        status = SignalQualityStatus.POOR
    return WaveformQualityResponse(
        signal_quality_score=score,
        signal_quality_status=status,
        clipping_fraction=clipping_fraction,
        flatline_fraction=flatline_fraction,
        motion_correlation=motion_correlation,
        usable=status != SignalQualityStatus.POOR,
    )


def assess_camera_frame_quality(request: CameraFrameQualityRequest) -> CameraFrameQualityResponse:
    """Evaluate capture conditions only; no image or disease interpretation occurs here."""

    score = 1.0
    reasons: list[str] = []
    guidance: list[str] = []
    if request.mean_luminance < 45:
        score -= 0.35
        reasons.append("underexposed")
        guidance.append("Increase steady, diffuse lighting")
    elif request.mean_luminance > 210:
        score -= 0.35
        reasons.append("overexposed")
        guidance.append("Reduce glare or direct light")
    if request.luminance_stddev < 12:
        score -= 0.20
        reasons.append("insufficient contrast")
        guidance.append("Reposition the camera and subject")
    if request.blur_variance < 80:
        score -= 0.30
        reasons.append("blurred")
        guidance.append("Hold the device steady and refocus")
    if request.motion_score > 0.25:
        score -= 0.30
        reasons.append("excessive motion")
        guidance.append("Keep the device and subject still")
    if request.clipped_dark_fraction > 0.10 or request.clipped_bright_fraction > 0.10:
        score -= 0.25
        reasons.append("pixel clipping")
        guidance.append("Use even lighting without deep shadows or highlights")
    score = max(0.0, min(1.0, score))
    return CameraFrameQualityResponse(
        accepted=score >= 0.70,
        score=score,
        reasons=reasons,
        guidance=guidance,
    )


# Compatibility alias for old internal imports.
assess_scalar_quality = assess_record_integrity
