"""Device-capability persistence and event-quality enrichment."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member2 import DeviceCapability, DeviceRegistry
from app.schemas.member2 import (
    CalibrationStatus,
    DeviceCapabilityBatchResponse,
    DeviceCapabilityResponse,
    DeviceCapabilityUpsertRequest,
    DeviceSupportStatus,
    HealthEventCreate,
    QualityDecision,
)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _response(row: DeviceCapability) -> DeviceCapabilityResponse:
    return DeviceCapabilityResponse(
        id=row.id,
        user_id=row.user_id,
        device_id=row.device_id,
        metric=row.metric,
        source_record_type=row.source_record_type,
        source_type=row.source_type,
        support_status=row.support_status,
        canonical_unit_ucum=row.canonical_unit_ucum,
        body_site=row.body_site,
        sampling_rate_min_hz=row.sampling_rate_min_hz,
        sampling_rate_max_hz=row.sampling_rate_max_hz,
        measurement_resolution=row.measurement_resolution,
        recording_methods=row.recording_methods_json,
        reference_method=row.reference_method,
        calibration_status=row.calibration_status,
        calibration_valid_until=_as_utc(row.calibration_valid_until),
        validation_protocol_version=row.validation_protocol_version,
        known_limitations=row.known_limitations_json,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


async def upsert_device_capabilities(
    session: AsyncSession,
    user_id: int,
    request: DeviceCapabilityUpsertRequest,
) -> DeviceCapabilityBatchResponse:
    for capability in request.capabilities:
        if capability.support_status != DeviceSupportStatus.EXPERIMENTAL:
            raise ValueError(
                "client capability declarations cannot self-certify a support status"
            )
        if capability.calibration_status != CalibrationStatus.UNVERIFIED:
            raise ValueError("client capability declarations cannot assert calibration")
        if capability.reference_method or capability.validation_protocol_version:
            raise ValueError("validation evidence is managed by the trusted server registry")
    device = await session.execute(
        select(DeviceRegistry).where(
            DeviceRegistry.user_id == user_id,
            DeviceRegistry.device_id == request.device_id,
        )
    )
    if device.scalar_one_or_none() is None:
        raise ValueError("device must be registered before capabilities are recorded")

    rows: list[DeviceCapability] = []
    for capability in request.capabilities:
        result = await session.execute(
            select(DeviceCapability).where(
                DeviceCapability.user_id == user_id,
                DeviceCapability.device_id == request.device_id,
                DeviceCapability.metric == capability.metric.value,
                DeviceCapability.source_record_type == capability.source_record_type,
            )
        )
        row = result.scalar_one_or_none()
        values = capability.model_dump(mode="python")
        values["metric"] = capability.metric.value
        values["source_type"] = capability.source_type.value
        values["support_status"] = capability.support_status.value
        values["recording_methods_json"] = [item.value for item in capability.recording_methods]
        values["known_limitations_json"] = values.pop("known_limitations")
        values["calibration_status"] = capability.calibration_status.value
        values.pop("recording_methods")
        if row is None:
            row = DeviceCapability(user_id=user_id, device_id=request.device_id, **values)
            session.add(row)
        else:
            for name, value in values.items():
                setattr(row, name, value)
        rows.append(row)
    await session.commit()
    for row in rows:
        await session.refresh(row)
    return DeviceCapabilityBatchResponse(
        device_id=request.device_id,
        capabilities=[_response(row) for row in rows],
    )


async def enrich_event_with_device_capability(
    session: AsyncSession,
    event: HealthEventCreate,
) -> HealthEventCreate:
    if event.device_id is None:
        return event
    result = await session.execute(
        select(DeviceCapability).where(
            DeviceCapability.user_id == event.user_id,
            DeviceCapability.device_id == event.device_id,
            DeviceCapability.metric == event.metric.value,
            DeviceCapability.source_record_type == event.source_record_type,
        )
    )
    capability = result.scalar_one_or_none()
    if capability is None:
        return event

    support_confidence = {
        DeviceSupportStatus.SUPPORTED.value: 1.0,
        DeviceSupportStatus.EXPERIMENTAL.value: 0.60,
        DeviceSupportStatus.RESEARCH_ONLY.value: 0.30,
        DeviceSupportStatus.DEPRECATED.value: 0.20,
        DeviceSupportStatus.BLOCKED.value: 0.0,
    }[capability.support_status]
    calibration_confidence = {
        CalibrationStatus.VALID.value: 1.0,
        CalibrationStatus.NOT_REQUIRED.value: 1.0,
        CalibrationStatus.EXPIRED.value: 0.0,
        CalibrationStatus.UNVERIFIED.value: None,
    }[capability.calibration_status]
    reasons = [
        reason
        for reason in event.quality_vector.reason_codes
        if reason not in {"device_validation_unavailable", "calibration_unverified"}
    ]
    decision = event.quality_vector.decision
    if capability.support_status == DeviceSupportStatus.BLOCKED.value:
        decision = QualityDecision.REJECTED
        reasons.append("device_capability_blocked")
    elif capability.support_status in {
        DeviceSupportStatus.RESEARCH_ONLY.value,
        DeviceSupportStatus.DEPRECATED.value,
    }:
        decision = QualityDecision.UNKNOWN
        reasons.append(f"device_capability_{capability.support_status}")
    if (
        event.sampling_rate_hz is not None
        and capability.sampling_rate_min_hz is not None
        and event.sampling_rate_hz < capability.sampling_rate_min_hz
    ) or (
        event.sampling_rate_hz is not None
        and capability.sampling_rate_max_hz is not None
        and event.sampling_rate_hz > capability.sampling_rate_max_hz
    ):
        decision = QualityDecision.REJECTED
        reasons.append("sampling_rate_outside_device_capability")
    vector = event.quality_vector.model_copy(
        update={
            "decision": decision,
            "device_validation_confidence": support_confidence,
            "calibration_confidence": calibration_confidence,
            "reason_codes": list(dict.fromkeys(reasons)),
        }
    )
    return event.model_copy(update={"quality_vector": vector})


__all__ = ["enrich_event_with_device_capability", "upsert_device_capabilities"]
