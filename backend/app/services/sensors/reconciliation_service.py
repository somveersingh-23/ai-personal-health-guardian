"""Resumable, idempotent and bounded-memory reconciliation workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member2 import (
    HealthEvent,
    ReconciliationRecord,
    ReconciliationSession,
    SourceTombstone,
)
from app.schemas.member2 import (
    ReconciliationChunkResponse,
    ReconciliationCompleteResponse,
    ReconciliationRecordChunk,
    ReconciliationSessionCreate,
    ReconciliationSessionResponse,
)

SESSION_TTL = timedelta(hours=2)
DELETE_BATCH_SIZE = 500


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _session_response(row: ReconciliationSession) -> ReconciliationSessionResponse:
    return ReconciliationSessionResponse(
        session_id=row.session_id,
        source=row.source,
        source_record_type=row.source_record_type,
        window_start=_as_utc(row.window_start),
        window_end=_as_utc(row.window_end),
        status=row.status,
        received_record_count=row.received_record_count,
        tombstoned_stale_count=row.tombstoned_stale_count,
        created_at=_as_utc(row.created_at),
        expires_at=_as_utc(row.expires_at),
        completed_at=_as_utc(row.completed_at),
    )


async def begin_reconciliation(
    session: AsyncSession,
    user_id: int,
    request: ReconciliationSessionCreate,
    now: datetime | None = None,
) -> ReconciliationSessionResponse:
    created_at = now or datetime.now(UTC)
    existing = await session.execute(
        select(ReconciliationSession).where(
            ReconciliationSession.session_id == str(request.session_id)
        )
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        if (
            row.user_id != user_id
            or row.source != request.source.value
            or row.source_record_type != request.source_record_type
            or _as_utc(row.window_start) != request.window_start.astimezone(UTC)
            or _as_utc(row.window_end) != request.window_end.astimezone(UTC)
        ):
            raise ValueError("reconciliation session IDs are immutable and globally unique")
        return _session_response(row)
    row = ReconciliationSession(
        session_id=str(request.session_id),
        user_id=user_id,
        source=request.source.value,
        source_record_type=request.source_record_type,
        window_start=request.window_start,
        window_end=request.window_end,
        status="collecting",
        received_record_count=0,
        tombstoned_stale_count=0,
        created_at=created_at,
        expires_at=created_at + SESSION_TTL,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _session_response(row)


async def add_reconciliation_records(
    session: AsyncSession,
    user_id: int,
    session_id: UUID,
    chunk: ReconciliationRecordChunk,
    now: datetime | None = None,
) -> ReconciliationChunkResponse:
    current = now or datetime.now(UTC)
    result = await session.execute(
        select(ReconciliationSession).where(
            ReconciliationSession.session_id == str(session_id),
            ReconciliationSession.user_id == user_id,
        )
    )
    reconciliation = result.scalar_one_or_none()
    if reconciliation is None:
        raise ValueError("reconciliation session was not found")
    if reconciliation.status != "collecting":
        raise ValueError("reconciliation session is not collecting")
    if _as_utc(reconciliation.expires_at) <= current:
        reconciliation.status = "aborted"
        await session.commit()
        raise ValueError("reconciliation session expired")

    existing = await session.execute(
        select(ReconciliationRecord.source_record_id).where(
            ReconciliationRecord.session_id == str(session_id),
            ReconciliationRecord.source_record_id.in_(chunk.source_record_ids),
        )
    )
    duplicate_ids = set(existing.scalars().all())
    new_ids = [item for item in chunk.source_record_ids if item not in duplicate_ids]
    session.add_all(
        [
            ReconciliationRecord(session_id=str(session_id), source_record_id=record_id)
            for record_id in new_ids
        ]
    )
    reconciliation.received_record_count += len(new_ids)
    await session.commit()
    return ReconciliationChunkResponse(
        session_id=session_id,
        received_count=len(new_ids),
        duplicate_count=len(duplicate_ids),
        total_unique_count=reconciliation.received_record_count,
    )


async def complete_reconciliation(
    session: AsyncSession,
    user_id: int,
    session_id: UUID,
    now: datetime | None = None,
) -> ReconciliationCompleteResponse:
    completed_at = now or datetime.now(UTC)
    result = await session.execute(
        select(ReconciliationSession).where(
            ReconciliationSession.session_id == str(session_id),
            ReconciliationSession.user_id == user_id,
        )
    )
    reconciliation = result.scalar_one_or_none()
    if reconciliation is None:
        raise ValueError("reconciliation session was not found")
    if reconciliation.status == "completed":
        return ReconciliationCompleteResponse(
            session_id=session_id,
            authoritative_count=reconciliation.received_record_count,
            tombstoned_stale_count=reconciliation.tombstoned_stale_count,
            completed_at=_as_utc(reconciliation.completed_at),
        )
    if reconciliation.status != "collecting":
        raise ValueError("reconciliation session cannot be completed")
    if _as_utc(reconciliation.expires_at) <= completed_at:
        reconciliation.status = "aborted"
        await session.commit()
        raise ValueError("reconciliation session expired")

    authoritative_ids = select(ReconciliationRecord.source_record_id).where(
        ReconciliationRecord.session_id == str(session_id)
    )
    total_deleted = 0
    last_id = 0
    while True:
        stale_result = await session.execute(
            select(HealthEvent)
            .where(
                HealthEvent.id > last_id,
                HealthEvent.user_id == user_id,
                HealthEvent.source == reconciliation.source,
                HealthEvent.source_record_type == reconciliation.source_record_type,
                HealthEvent.source_record_id.is_not(None),
                HealthEvent.source_record_id.not_in(authoritative_ids),
                (
                    (
                        (HealthEvent.observed_at >= reconciliation.window_start)
                        & (HealthEvent.observed_at < reconciliation.window_end)
                    )
                    | (
                        (HealthEvent.start_at < reconciliation.window_end)
                        & (HealthEvent.end_at > reconciliation.window_start)
                    )
                ),
            )
            .order_by(HealthEvent.id)
            .limit(DELETE_BATCH_SIZE)
        )
        stale_rows = list(stale_result.scalars().all())
        if not stale_rows:
            break
        stale_ids = [row.id for row in stale_rows]
        last_id = stale_ids[-1]
        for row in stale_rows:
            session.add(
                SourceTombstone(
                    user_id=user_id,
                    event_id=row.event_id,
                    source=row.source,
                    source_record_type=row.source_record_type,
                    source_record_id=row.source_record_id,
                    consent_receipt_id=row.consent_receipt_id,
                    reason="staged_expired_token_reconciliation",
                    deleted_at=completed_at,
                )
            )
        await session.execute(
            delete(HealthEvent)
            .where(HealthEvent.id.in_(stale_ids))
            .execution_options(synchronize_session=False)
        )
        total_deleted += len(stale_rows)
        await session.flush()

    reconciliation.status = "completed"
    reconciliation.completed_at = completed_at
    reconciliation.tombstoned_stale_count = total_deleted
    await session.execute(
        delete(ReconciliationRecord).where(
            ReconciliationRecord.session_id == str(session_id)
        )
    )
    await session.commit()
    return ReconciliationCompleteResponse(
        session_id=session_id,
        authoritative_count=reconciliation.received_record_count,
        tombstoned_stale_count=total_deleted,
        completed_at=completed_at,
    )


__all__ = [
    "add_reconciliation_records",
    "begin_reconciliation",
    "complete_reconciliation",
]
