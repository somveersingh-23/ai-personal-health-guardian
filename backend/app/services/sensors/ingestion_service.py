"""Normalize typed connector records into server-trusted HealthEvents."""

from datetime import UTC, datetime

from app.schemas.member2 import (
    CANONICAL_UCUM_UNITS,
    LOINC_CODES,
    HealthEventBatchPreviewRequest,
    HealthEventBatchPreviewResponse,
    HealthEventCreate,
    ReadingCreate,
)
from app.services.sensors.deduplication_service import deduplicate_batch
from app.services.sensors.quality_service import assess_record_integrity


def normalize_reading(
    reading: ReadingCreate,
    user_id: int,
    received_at: datetime | None = None,
) -> HealthEventCreate:
    received = received_at or datetime.now(UTC)
    assessment = assess_record_integrity(reading, received)
    payload = reading.model_dump()
    payload["data_origin_package"] = reading.data_origin_package or reading.source.value
    payload["source_record_type"] = (
        reading.source_record_type or f"{reading.metric.value}:{reading.temporal_type.value}"
    )
    payload["source_unit"] = reading.unit
    payload["canonical_unit_ucum"] = CANONICAL_UCUM_UNITS[reading.metric]
    loinc = LOINC_CODES[reading.metric]
    payload["standard_code_system"] = "http://loinc.org" if loinc else None
    payload["standard_code"] = loinc
    return HealthEventCreate(
        **payload,
        user_id=user_id,
        record_integrity_score=assessment.record_integrity_score,
        record_integrity_status=assessment.record_integrity_status,
        signal_quality_score=assessment.signal_quality_score,
        signal_quality_status=assessment.signal_quality_status,
        freshness_status=assessment.freshness_status,
        data_freshness_seconds=assessment.data_freshness_seconds,
        validation_flag=assessment.validation_flag,
        validation_reason=assessment.validation_reason,
        quality_vector=assessment.quality_vector,
        quality_policy_version=assessment.quality_vector.policy_version,
    )


def normalize_batch_readings(
    batch: HealthEventBatchPreviewRequest,
    received_at: datetime | None = None,
) -> HealthEventBatchPreviewResponse:
    received = received_at or datetime.now(UTC)
    unique, duplicates = deduplicate_batch(batch.events, batch.user_id)
    events = [normalize_reading(item, batch.user_id, received) for item in unique]
    return HealthEventBatchPreviewResponse(
        batch_id=batch.batch_id,
        received_count=len(batch.events),
        normalized_count=len(events),
        duplicate_count=len(duplicates),
        events=events,
    )


normalize_scalar_reading = normalize_reading
