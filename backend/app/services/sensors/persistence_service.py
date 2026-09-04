"""Transactional persistence, idempotency, deletion, device, and sync-state operations."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member2 import (
    DeviceRegistry,
    HealthConnectSyncState,
    HealthEvent,
    SensorIngestionAudit,
    SourceTombstone,
)
from app.schemas.member2 import (
    DeviceInfo,
    HealthConnectSyncCursor,
    HealthEventBatchCreate,
    HealthEventBatchResponse,
    HealthEventCreate,
    HealthEventResponse,
    IntegrityStatus,
    MetricType,
    QualityDecision,
    SourceDeletionRequest,
    SourceReconciliationRequest,
)
from app.services.sensors.capability_service import enrich_event_with_device_capability
from app.services.sensors.deduplication_service import deduplicate_batch
from app.services.sensors.governance_service import validate_event_consents
from app.services.sensors.ingestion_service import normalize_reading


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite drops timezone metadata; PostgreSQL does not. Normalize both at the boundary."""

    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _event_fields(event: HealthEventCreate) -> dict[str, object]:
    return {
        "event_id": str(event.event_id),
        "schema_version": event.schema_version,
        "user_id": event.user_id,
        "temporal_type": event.temporal_type.value,
        "metric": event.metric.value,
        "unit": event.unit,
        "source_unit": event.source_unit,
        "canonical_unit_ucum": event.canonical_unit_ucum,
        "standard_code_system": event.standard_code_system,
        "standard_code": event.standard_code,
        "source": event.source.value,
        "observed_at": event.observed_at,
        "start_at": event.start_at,
        "end_at": event.end_at,
        "timezone_offset_minutes": event.timezone_offset_minutes,
        "start_timezone_offset_minutes": event.start_timezone_offset_minutes,
        "end_timezone_offset_minutes": event.end_timezone_offset_minutes,
        "value": event.value,
        "samples_json": [sample.model_dump(mode="json") for sample in event.samples],
        "stages_json": [stage.model_dump(mode="json") for stage in event.stages],
        "data_origin_package": event.data_origin_package,
        "source_record_type": event.source_record_type,
        "source_record_id": event.source_record_id,
        "client_record_id": event.client_record_id,
        "client_record_version": event.client_record_version,
        "source_last_modified_at": event.source_last_modified_at,
        "device_id": event.device_id,
        "device_manufacturer": event.device_manufacturer,
        "device_model": event.device_model,
        "device_type": event.device_type,
        "body_site": event.body_site,
        "sampling_rate_hz": event.sampling_rate_hz,
        "wear_state": event.wear_state.value,
        "motion_state": event.motion_state.value,
        "motion_artifact_score": event.motion_artifact_score,
        "recording_method": event.recording_method.value,
        "permission_state": event.permission_state.value,
        "consent_receipt_id": str(event.consent_receipt_id) if event.consent_receipt_id else None,
        "processing_purpose": event.processing_purpose.value,
        "purpose_version": event.purpose_version,
        "retention_class": event.retention_class.value,
        "mapper_version": event.mapper_version,
        "metadata_json": event.metadata,
        "record_integrity_score": event.record_integrity_score,
        "record_integrity_status": event.record_integrity_status.value,
        "signal_quality_score": event.signal_quality_score,
        "signal_quality_status": event.signal_quality_status.value,
        "freshness_status": event.freshness_status.value,
        "data_freshness_seconds": event.data_freshness_seconds,
        "validation_flag": event.validation_flag.value,
        "validation_reason": event.validation_reason,
        "quality_policy_version": event.quality_policy_version,
        "quality_vector_json": event.quality_vector.model_dump(mode="json"),
        "lifecycle_status": event.lifecycle_status.value,
        "deleted_at": event.deleted_at,
        "deletion_reason": event.deletion_reason,
    }


def event_from_orm(row: HealthEvent) -> HealthEventCreate:
    return HealthEventCreate.model_validate(
        {
            "schema_version": row.schema_version,
            "event_id": row.event_id,
            "user_id": row.user_id,
            "temporal_type": row.temporal_type,
            "metric": row.metric,
            "unit": row.unit,
            "source_unit": row.source_unit,
            "canonical_unit_ucum": row.canonical_unit_ucum,
            "standard_code_system": row.standard_code_system,
            "standard_code": row.standard_code,
            "source": row.source,
            "observed_at": as_utc(row.observed_at),
            "start_at": as_utc(row.start_at),
            "end_at": as_utc(row.end_at),
            "timezone_offset_minutes": row.timezone_offset_minutes,
            "start_timezone_offset_minutes": row.start_timezone_offset_minutes,
            "end_timezone_offset_minutes": row.end_timezone_offset_minutes,
            "value": row.value,
            "samples": row.samples_json,
            "stages": row.stages_json,
            "data_origin_package": row.data_origin_package,
            "source_record_type": row.source_record_type,
            "source_record_id": row.source_record_id,
            "client_record_id": row.client_record_id,
            "client_record_version": row.client_record_version,
            "source_last_modified_at": as_utc(row.source_last_modified_at),
            "device_id": row.device_id,
            "device_manufacturer": row.device_manufacturer,
            "device_model": row.device_model,
            "device_type": row.device_type,
            "body_site": row.body_site,
            "sampling_rate_hz": row.sampling_rate_hz,
            "wear_state": row.wear_state,
            "motion_state": row.motion_state,
            "motion_artifact_score": row.motion_artifact_score,
            "recording_method": row.recording_method,
            "permission_state": row.permission_state,
            "consent_receipt_id": row.consent_receipt_id,
            "processing_purpose": row.processing_purpose,
            "purpose_version": row.purpose_version,
            "retention_class": row.retention_class,
            "mapper_version": row.mapper_version,
            "metadata": row.metadata_json,
            "record_integrity_score": row.record_integrity_score,
            "record_integrity_status": row.record_integrity_status,
            "signal_quality_score": row.signal_quality_score,
            "signal_quality_status": row.signal_quality_status,
            "freshness_status": row.freshness_status,
            "data_freshness_seconds": row.data_freshness_seconds,
            "validation_flag": row.validation_flag,
            "validation_reason": row.validation_reason,
            "quality_policy_version": row.quality_policy_version,
            "quality_vector": row.quality_vector_json,
            "lifecycle_status": row.lifecycle_status,
            "deleted_at": as_utc(row.deleted_at),
            "deletion_reason": row.deletion_reason,
        }
    )


def event_response_from_orm(row: HealthEvent) -> HealthEventResponse:
    return HealthEventResponse(
        **event_from_orm(row).model_dump(),
        id=row.id,
        ingested_at=as_utc(row.ingested_at),
        updated_at=as_utc(row.updated_at),
    )


async def _find_existing(session: AsyncSession, event: HealthEventCreate) -> HealthEvent | None:
    clauses = [HealthEvent.event_id == str(event.event_id)]
    if event.source_record_id is not None:
        clauses.append(
            and_(
                HealthEvent.user_id == event.user_id,
                HealthEvent.data_origin_package == event.data_origin_package,
                HealthEvent.source_record_type == event.source_record_type,
                HealthEvent.source_record_id == event.source_record_id,
            )
        )
    result = await session.execute(select(HealthEvent).where(or_(*clauses)))
    return result.scalars().first()


async def _find_tombstone(session: AsyncSession, event: HealthEventCreate) -> SourceTombstone | None:
    if event.source_record_id is None:
        return None
    result = await session.execute(
        select(SourceTombstone).where(
            SourceTombstone.user_id == event.user_id,
            SourceTombstone.source == event.source.value,
            SourceTombstone.source_record_type == event.source_record_type,
            SourceTombstone.source_record_id == event.source_record_id,
        )
    )
    return result.scalar_one_or_none()


def _should_update(existing: HealthEvent, incoming: HealthEventCreate) -> bool:
    if incoming.source_last_modified_at is None:
        return False
    if existing.source_last_modified_at is None:
        return True
    existing_time = existing.source_last_modified_at
    if existing_time.tzinfo is None:
        existing_time = existing_time.replace(tzinfo=UTC)
    return incoming.source_last_modified_at > existing_time


async def persist_batch(
    session: AsyncSession,
    batch: HealthEventBatchCreate,
    user_id: int,
    received_at: datetime | None = None,
) -> HealthEventBatchResponse:
    """Atomically insert/update a fully valid batch and record only a payload fingerprint."""

    received = received_at or datetime.now(UTC)
    unique, request_duplicates = deduplicate_batch(batch.events, user_id)
    normalized = [normalize_reading(reading, user_id, received) for reading in unique]
    await validate_event_consents(session, user_id, normalized, received)
    normalized = [
        await enrich_event_with_device_capability(session, event) for event in normalized
    ]
    if any(event.record_integrity_status == IntegrityStatus.REJECTED for event in normalized):
        raise ValueError("batch contains a rejected record; no records were persisted")
    if any(event.quality_vector.decision == QualityDecision.REJECTED for event in normalized):
        raise ValueError("batch contains a record rejected by device capability policy")

    inserted = 0
    updated = 0
    duplicate_count = len(request_duplicates)
    rows: list[HealthEvent] = []
    try:
        for event in normalized:
            tombstone = await _find_tombstone(session, event)
            if tombstone is not None:
                deleted_at = as_utc(tombstone.deleted_at)
                modified_at = event.source_last_modified_at
                if modified_at is None or deleted_at is None or modified_at <= deleted_at:
                    duplicate_count += 1
                    continue
                await session.delete(tombstone)
            existing = await _find_existing(session, event)
            if existing is not None:
                if existing.user_id != user_id:
                    raise ValueError("event_id collision across users")
                if _should_update(existing, event):
                    for name, value in _event_fields(event).items():
                        setattr(existing, name, value)
                    existing.updated_at = received
                    updated += 1
                else:
                    duplicate_count += 1
                rows.append(existing)
                continue
            row = HealthEvent(**_event_fields(event))
            session.add(row)
            rows.append(row)
            inserted += 1

        raw = batch.model_dump_json().encode("utf-8")
        sources = sorted({event.source.value for event in normalized})
        session.add(
            SensorIngestionAudit(
                payload_sha256=hashlib.sha256(raw).hexdigest(),
                payload_size_bytes=len(raw),
                event_count=len(batch.events),
                user_id=user_id,
                source=",".join(sources)[:64],
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    for row in rows:
        await session.refresh(row)
    return HealthEventBatchResponse(
        batch_id=batch.batch_id,
        received_count=len(batch.events),
        inserted_count=inserted,
        updated_count=updated,
        duplicate_count=duplicate_count,
        events=[event_response_from_orm(row) for row in rows],
    )


async def fetch_events_for_window(
    session: AsyncSession,
    user_id: int,
    metrics: list[MetricType],
    window_start: datetime,
    window_end: datetime,
) -> list[HealthEventCreate]:
    result = await session.execute(
        select(HealthEvent).where(
            HealthEvent.user_id == user_id,
            HealthEvent.metric.in_([metric.value for metric in metrics]),
            HealthEvent.lifecycle_status != "deleted",
            or_(
                and_(HealthEvent.observed_at >= window_start, HealthEvent.observed_at < window_end),
                and_(HealthEvent.start_at < window_end, HealthEvent.end_at > window_start),
            ),
        )
    )
    return [event_from_orm(row) for row in result.scalars().all()]


async def delete_source_records(
    session: AsyncSession,
    user_id: int,
    request: SourceDeletionRequest,
) -> int:
    deletion_time = request.deleted_at or datetime.now(UTC)
    records = await session.execute(
        select(HealthEvent).where(
            HealthEvent.user_id == user_id,
            HealthEvent.source == request.source.value,
            HealthEvent.source_record_type == request.source_record_type,
            HealthEvent.source_record_id.in_(request.source_record_ids),
        )
    )
    rows = list(records.scalars().all())
    existing_tombstones = await session.execute(
        select(SourceTombstone.source_record_id).where(
            SourceTombstone.user_id == user_id,
            SourceTombstone.source == request.source.value,
            SourceTombstone.source_record_type == request.source_record_type,
            SourceTombstone.source_record_id.in_(request.source_record_ids),
        )
    )
    tombstoned = set(existing_tombstones.scalars().all())
    rows_by_source_id = {row.source_record_id: row for row in rows}
    for source_record_id in request.source_record_ids:
        if source_record_id in tombstoned:
            continue
        row = rows_by_source_id.get(source_record_id)
        session.add(
            SourceTombstone(
                user_id=user_id,
                event_id=row.event_id if row else None,
                source=request.source.value,
                source_record_type=request.source_record_type,
                source_record_id=source_record_id,
                consent_receipt_id=row.consent_receipt_id if row else None,
                reason="source_deletion",
                deleted_at=deletion_time,
            )
        )
    result = await session.execute(
        delete(HealthEvent).where(
            HealthEvent.user_id == user_id,
            HealthEvent.source == request.source.value,
            HealthEvent.source_record_type == request.source_record_type,
            HealthEvent.source_record_id.in_(request.source_record_ids),
        ).execution_options(synchronize_session=False)
    )
    await session.commit()
    return int(result.rowcount or 0)


async def reconcile_source_records(
    session: AsyncSession,
    user_id: int,
    request: SourceReconciliationRequest,
) -> int:
    """Serve the legacy bounded reconciliation endpoint with tombstone protection."""

    conditions = [
        HealthEvent.user_id == user_id,
        HealthEvent.source == request.source.value,
        HealthEvent.source_record_type == request.source_record_type,
        HealthEvent.source_record_id.is_not(None),
        or_(
            and_(
                HealthEvent.observed_at >= request.window_start,
                HealthEvent.observed_at < request.window_end,
            ),
            and_(HealthEvent.start_at < request.window_end, HealthEvent.end_at > request.window_start),
        ),
    ]
    if request.source_record_ids:
        conditions.append(HealthEvent.source_record_id.not_in(request.source_record_ids))
    stale = await session.execute(select(HealthEvent).where(*conditions))
    rows = list(stale.scalars().all())
    for row in rows:
        existing = await session.execute(
            select(SourceTombstone).where(
                SourceTombstone.user_id == user_id,
                SourceTombstone.source == request.source.value,
                SourceTombstone.source_record_type == request.source_record_type,
                SourceTombstone.source_record_id == row.source_record_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(
                SourceTombstone(
                    user_id=user_id,
                    event_id=row.event_id,
                    source=request.source.value,
                    source_record_type=request.source_record_type,
                    source_record_id=row.source_record_id,
                    consent_receipt_id=row.consent_receipt_id,
                    reason="expired_token_reconciliation",
                    deleted_at=datetime.now(UTC),
                )
            )
    result = await session.execute(
        delete(HealthEvent).where(*conditions).execution_options(synchronize_session=False)
    )
    await session.commit()
    return int(result.rowcount or 0)


async def upsert_device(session: AsyncSession, user_id: int, device: DeviceInfo) -> DeviceRegistry:
    result = await session.execute(
        select(DeviceRegistry).where(
            DeviceRegistry.user_id == user_id,
            DeviceRegistry.device_id == device.device_id,
        )
    )
    row = result.scalar_one_or_none()
    values = device.model_dump()
    values["source_type"] = device.source_type.value
    values["permission_state"] = device.permission_state.value
    values["metadata_json"] = values.pop("metadata")
    if row is None:
        row = DeviceRegistry(user_id=user_id, **values)
        session.add(row)
    else:
        for name, value in values.items():
            setattr(row, name, value)
    await session.commit()
    await session.refresh(row)
    return row


async def upsert_sync_cursor(
    session: AsyncSession,
    user_id: int,
    cursor: HealthConnectSyncCursor,
) -> HealthConnectSyncState:
    result = await session.execute(
        select(HealthConnectSyncState).where(
            HealthConnectSyncState.user_id == user_id,
            HealthConnectSyncState.record_type == cursor.record_type,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = HealthConnectSyncState(
            user_id=user_id,
            record_type=cursor.record_type,
            changes_token="redacted",
            token_fingerprint=cursor.token_fingerprint,
            last_successful_sync_at=cursor.last_successful_sync_at,
        )
        session.add(row)
    else:
        row.changes_token = "redacted"
        row.token_fingerprint = cursor.token_fingerprint
        row.last_successful_sync_at = cursor.last_successful_sync_at
    await session.commit()
    await session.refresh(row)
    return row
