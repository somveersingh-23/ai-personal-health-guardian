"""Consent validation, purpose limitation, withdrawal, and deletion cascade."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member2 import ConsentReceipt, HealthEvent, SourceTombstone
from app.schemas.member2 import (
    ConsentReceiptCreate,
    ConsentReceiptResponse,
    ConsentStatus,
    ConsentWithdrawalRequest,
    ConsentWithdrawalResponse,
    HealthEventCreate,
)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def consent_response_from_orm(row: ConsentReceipt) -> ConsentReceiptResponse:
    return ConsentReceiptResponse(
        id=row.id,
        receipt_id=row.receipt_id,
        user_id=row.user_id,
        purpose=row.purpose,
        purpose_version=row.purpose_version,
        notice_version=row.notice_version,
        granted_metrics=row.granted_metrics_json,
        granted_sources=row.granted_sources_json,
        status=row.status,
        consented_at=_as_utc(row.consented_at),
        expires_at=_as_utc(row.expires_at),
        withdrawn_at=_as_utc(row.withdrawn_at),
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
    )


async def create_consent_receipt(
    session: AsyncSession,
    user_id: int,
    receipt: ConsentReceiptCreate,
) -> ConsentReceiptResponse:
    existing = await session.execute(
        select(ConsentReceipt).where(ConsentReceipt.receipt_id == str(receipt.receipt_id))
    )
    row = existing.scalar_one_or_none()
    values = receipt.model_dump(mode="python")
    values["receipt_id"] = str(receipt.receipt_id)
    values["purpose"] = receipt.purpose.value
    values["granted_sources_json"] = [item.value for item in receipt.granted_sources]
    values["granted_metrics_json"] = values.pop("granted_metrics")
    values.pop("granted_sources")
    if row is not None:
        comparable = {
            "receipt_id": row.receipt_id,
            "purpose": row.purpose,
            "purpose_version": row.purpose_version,
            "notice_version": row.notice_version,
            "granted_metrics_json": row.granted_metrics_json,
            "granted_sources_json": row.granted_sources_json,
            "consented_at": _as_utc(row.consented_at).isoformat(),
            "expires_at": _as_utc(row.expires_at).isoformat() if row.expires_at else None,
        }
        incoming = {
            **values,
            "consented_at": receipt.consented_at.isoformat(),
            "expires_at": receipt.expires_at.isoformat() if receipt.expires_at else None,
        }
        if row.user_id != user_id or comparable != incoming:
            raise ValueError("consent receipt IDs are immutable and globally unique")
        return consent_response_from_orm(row)
    row = ConsentReceipt(user_id=user_id, status=ConsentStatus.ACTIVE.value, **values)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return consent_response_from_orm(row)


async def validate_event_consents(
    session: AsyncSession,
    user_id: int,
    events: list[HealthEventCreate],
    now: datetime,
) -> None:
    v3_events = [event for event in events if event.schema_version == "3.0.0"]
    if not v3_events:
        return
    receipt_ids = {str(event.consent_receipt_id) for event in v3_events}
    result = await session.execute(
        select(ConsentReceipt).where(
            ConsentReceipt.user_id == user_id,
            ConsentReceipt.receipt_id.in_(receipt_ids),
        )
    )
    receipts = {row.receipt_id: row for row in result.scalars().all()}
    for event in v3_events:
        receipt = receipts.get(str(event.consent_receipt_id))
        if receipt is None:
            raise ValueError("v3 event references an unknown consent receipt")
        expires_at = _as_utc(receipt.expires_at)
        if receipt.status != ConsentStatus.ACTIVE.value or (expires_at and expires_at <= now):
            raise ValueError("v3 event consent is not active")
        if receipt.purpose != event.processing_purpose.value:
            raise ValueError("event purpose does not match consent receipt")
        if receipt.purpose_version != event.purpose_version:
            raise ValueError("event purpose_version does not match consent receipt")
        if event.metric.value not in receipt.granted_metrics_json:
            raise ValueError(f"consent does not grant metric: {event.metric.value}")
        if event.source.value not in receipt.granted_sources_json:
            raise ValueError(f"consent does not grant source: {event.source.value}")


async def withdraw_consent(
    session: AsyncSession,
    user_id: int,
    receipt_id: UUID,
    request: ConsentWithdrawalRequest,
    now: datetime | None = None,
) -> ConsentWithdrawalResponse:
    withdrawn_at = now or datetime.now(UTC)
    result = await session.execute(
        select(ConsentReceipt).where(
            ConsentReceipt.user_id == user_id,
            ConsentReceipt.receipt_id == str(receipt_id),
        )
    )
    receipt = result.scalar_one_or_none()
    if receipt is None:
        raise ValueError("consent receipt was not found")
    receipt.status = ConsentStatus.WITHDRAWN.value
    receipt.withdrawn_at = withdrawn_at

    deleted_count = 0
    if request.delete_linked_observations:
        linked = await session.execute(
            select(HealthEvent).where(
                HealthEvent.user_id == user_id,
                HealthEvent.consent_receipt_id == str(receipt_id),
            )
        )
        rows = list(linked.scalars().all())
        existing = await session.execute(
            select(SourceTombstone.source_record_id).where(
                SourceTombstone.user_id == user_id,
                SourceTombstone.consent_receipt_id == str(receipt_id),
            )
        )
        tombstoned = set(existing.scalars().all())
        for row in rows:
            if row.source_record_id is None or row.source_record_id in tombstoned:
                continue
            session.add(
                SourceTombstone(
                    user_id=user_id,
                    event_id=row.event_id,
                    source=row.source,
                    source_record_type=row.source_record_type,
                    source_record_id=row.source_record_id,
                    consent_receipt_id=str(receipt_id),
                    reason=request.reason,
                    deleted_at=withdrawn_at,
                )
            )
        deleted = await session.execute(
            delete(HealthEvent).where(
                HealthEvent.user_id == user_id,
                HealthEvent.consent_receipt_id == str(receipt_id),
            ).execution_options(synchronize_session=False)
        )
        deleted_count = int(deleted.rowcount or 0)
    await session.commit()
    return ConsentWithdrawalResponse(
        receipt_id=receipt_id,
        deleted_observation_count=deleted_count,
    )


__all__ = [
    "consent_response_from_orm",
    "create_consent_receipt",
    "validate_event_consents",
    "withdraw_consent",
]
