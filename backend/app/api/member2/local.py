"""Local integration API for Member 2 sensor intelligence.

This project intentionally has no account authentication layer. These endpoints
therefore require an existing Member 1 ``user_id`` and are suitable only for a
trusted single-user/local deployment unless an external access boundary is added.
"""

from datetime import UTC, datetime
from uuid import UUID
from app.schemas.member2.privacy import Member2CollectionResumeRequest

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.models.member1.health_profile import HealthProfile
from app.schemas.member2 import (
    CLAIM_REGISTRY,
    ConsentReceiptCreate,
    ConsentReceiptResponse,
    ConsentWithdrawalRequest,
    ConsentWithdrawalResponse,
    DeviceCapabilityBatchResponse,
    DeviceCapabilityUpsertRequest,
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    FeatureClaim,
    HealthConnectSyncCursor,
    HealthConnectSyncCursorResponse,
    HealthEventBatchCreate,
    HealthEventBatchResponse,
    HealthEventResponse,
    MetricType,
    Member2DataExportPage,
    Member2DataPurgeRequest,
    Member2DataPurgeResponse,
    MultimodalFusionRequest,
    MultimodalFusionResponse,
    ReconciliationChunkResponse,
    ReconciliationCompleteRequest,
    ReconciliationCompleteResponse,
    ReconciliationRecordChunk,
    ReconciliationSessionCreate,
    ReconciliationSessionResponse,
    SourceDeletionRequest,
    SourceDeletionResponse,
    SourceReconciliationRequest,
    SourceReconciliationResponse,
)
from app.services.sensors import (
    add_reconciliation_records,
    begin_reconciliation,
    complete_reconciliation,
    create_consent_receipt,
    delete_source_records,
    fetch_events_for_window,
    export_active_events_page,
    fuse_events,
    list_active_events,
    persist_batch,
    purge_member2_data,
    reconcile_source_records,
    upsert_device,
    upsert_device_capabilities,
    upsert_sync_cursor,
    withdraw_consent,
)
from app.services.sensors.persistence_service import as_utc
from app.services.sensors.transactions import CollectionPausedError, resume_collection
from app.api.member2.errors import Member2Route

router = APIRouter(
    prefix="/api/v1/member2",
    tags=["Member 2 - Sensor Intelligence"],
    route_class=Member2Route,
)


async def require_local_profile(
    user_id: int = Query(gt=0), db: AsyncSession = Depends(get_db)
) -> int:
    """Reject accidental writes for a user that M1 has not initialized."""
    profile = await db.scalar(
        select(HealthProfile.id).where(HealthProfile.user_id == user_id).limit(1)
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create the Member 1 health profile before syncing sensor observations.",
        )
    return user_id


@router.get("/claims", response_model=list[FeatureClaim])
async def get_claim_boundaries() -> list[FeatureClaim]:
    return list(CLAIM_REGISTRY)


@router.post(
    "/consents",
    response_model=ConsentReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_consent(
    receipt: ConsentReceiptCreate,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> ConsentReceiptResponse:
    return await create_consent_receipt(db, user_id, receipt)


@router.post(
    "/consents/{receipt_id}/withdraw", response_model=ConsentWithdrawalResponse
)
async def revoke_consent(
    receipt_id: UUID,
    request: ConsentWithdrawalRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> ConsentWithdrawalResponse:
    try:
        return await withdraw_consent(db, user_id, receipt_id, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/events/batch", response_model=HealthEventBatchResponse)
async def ingest_events(
    batch: HealthEventBatchCreate,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> HealthEventBatchResponse:
    if any(
        event.source.value in {"research_dataset", "simulated"}
        for event in batch.events
    ):
        raise HTTPException(
            422,
            "offline research/simulated records cannot enter the live profile store",
        )
    try:
        return await persist_batch(db, batch, user_id, datetime.now(UTC))
    except CollectionPausedError:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get("/events", response_model=list[HealthEventResponse])
async def list_events(
    metrics: list[MetricType] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> list[HealthEventResponse]:
    """Stable M2 read model for M1 dashboards and later AI/RAG consumers."""
    return await list_active_events(db, user_id, metrics, limit)


@router.get("/data/export", response_model=Member2DataExportPage)
async def export_sensor_data(
    after_id: int | None = Query(default=None, ge=0),
    limit: int = Query(default=250, ge=1, le=500),
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> Member2DataExportPage:
    """Export active normalized observations in stable, bounded pages."""
    events, next_after_id, has_more = await export_active_events_page(
        db,
        user_id,
        after_id,
        limit,
    )
    return Member2DataExportPage(
        user_id=user_id,
        exported_at=datetime.now(UTC),
        events=events,
        next_after_id=next_after_id,
        has_more=has_more,
    )


@router.post("/data/purge", response_model=Member2DataPurgeResponse)
async def purge_sensor_domain_data(
    request: Member2DataPurgeRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> Member2DataPurgeResponse:
    """Permanently erase M2 data while preserving the M1-owned health profile."""
    del request
    counts = await purge_member2_data(db, user_id)
    return Member2DataPurgeResponse(
        user_id=user_id,
        deleted_counts=counts,
        completed_at=datetime.now(UTC),
    )


@router.post("/data/resume", response_model=dict[str, bool])
async def resume_sensor_collection(
    request: Member2CollectionResumeRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    del request
    await resume_collection(db, user_id)
    return {"collection_paused": False}


@router.post("/features/align", response_model=MultimodalFusionResponse)
async def align_features(
    request: MultimodalFusionRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> MultimodalFusionResponse:
    events = await fetch_events_for_window(
        db, user_id, request.requested_metrics, request.window_start, request.window_end
    )
    try:
        vector = fuse_events(
            events,
            request.requested_metrics,
            request.window_start,
            request.window_end,
            request.minimum_integrity_score,
            request.minimum_composite_quality,
            request.minimum_available_metrics,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return MultimodalFusionResponse(vector=vector)


@router.put("/devices", response_model=DeviceRegistrationResponse)
async def register_device(
    request: DeviceRegistrationRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> DeviceRegistrationResponse:
    row = await upsert_device(db, user_id, request.device)
    return DeviceRegistrationResponse(
        id=row.id,
        user_id=row.user_id,
        device_id=row.device_id,
        manufacturer=row.manufacturer,
        model=row.model,
        firmware_version=row.firmware_version,
        device_type=row.device_type,
        source_type=row.source_type,
        permission_state=row.permission_state,
        battery_level=row.battery_level,
        capabilities=row.capabilities,
        metadata=row.metadata_json,
        last_sync_time=as_utc(row.last_sync_time),
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
    )


@router.put("/devices/capabilities", response_model=DeviceCapabilityBatchResponse)
async def register_capabilities(
    request: DeviceCapabilityUpsertRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> DeviceCapabilityBatchResponse:
    return await upsert_device_capabilities(db, user_id, request)


@router.put("/sync/cursor", response_model=HealthConnectSyncCursorResponse)
async def save_sync_cursor(
    cursor: HealthConnectSyncCursor,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> HealthConnectSyncCursorResponse:
    row = await upsert_sync_cursor(db, user_id, cursor)
    return HealthConnectSyncCursorResponse(
        id=row.id,
        user_id=row.user_id,
        record_type=row.record_type,
        token_fingerprint=row.token_fingerprint,
        last_successful_sync_at=as_utc(row.last_successful_sync_at),
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
    )


@router.post("/sync/deletions", response_model=SourceDeletionResponse)
async def apply_deletions(
    request: SourceDeletionRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> SourceDeletionResponse:
    return await delete_source_records(db, user_id, request)


@router.post("/sync/reconcile", response_model=SourceReconciliationResponse)
async def reconcile_snapshot(
    request: SourceReconciliationRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> SourceReconciliationResponse:
    deleted = await reconcile_source_records(db, user_id, request)
    return SourceReconciliationResponse(
        authoritative_count=len(request.source_record_ids), deleted_stale_count=deleted
    )


@router.post(
    "/sync/reconcile/sessions",
    response_model=ReconciliationSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_reconciliation(
    request: ReconciliationSessionCreate,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationSessionResponse:
    return await begin_reconciliation(db, user_id, request)


@router.post(
    "/sync/reconcile/sessions/{session_id}/records",
    response_model=ReconciliationChunkResponse,
)
async def append_reconciliation(
    session_id: UUID,
    request: ReconciliationRecordChunk,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationChunkResponse:
    return await add_reconciliation_records(db, user_id, session_id, request)


@router.post(
    "/sync/reconcile/sessions/{session_id}/complete",
    response_model=ReconciliationCompleteResponse,
)
async def finish_reconciliation(
    session_id: UUID,
    request: ReconciliationCompleteRequest,
    user_id: int = Depends(require_local_profile),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationCompleteResponse:
    del request
    return await complete_reconciliation(db, user_id, session_id)
