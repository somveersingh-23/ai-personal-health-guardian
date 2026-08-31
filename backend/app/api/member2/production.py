"""Authenticated production APIs for Member 2 persistence and processing."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser, get_current_user
from app.database.database import get_db
from app.schemas.member2 import (
    CLAIM_REGISTRY,
    CameraFrameQualityRequest,
    CameraFrameQualityResponse,
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
    MultimodalEvidenceRequest,
    MultimodalEvidenceVector,
    MultimodalFusionRequest,
    MultimodalFusionResponse,
    QualityAssessmentResponse,
    ReconciliationChunkResponse,
    ReconciliationCompleteRequest,
    ReconciliationCompleteResponse,
    ReconciliationRecordChunk,
    ReconciliationSessionCreate,
    ReconciliationSessionResponse,
    RecordIntegrityAssessmentRequest,
    SourceDeletionRequest,
    SourceDeletionResponse,
    SourceReconciliationRequest,
    SourceReconciliationResponse,
    WaveformQualityAssessmentRequest,
    WaveformQualityResponse,
)
from app.services.sensors import (
    add_reconciliation_records,
    assess_camera_frame_quality,
    assess_record_integrity,
    assess_waveform_quality,
    begin_reconciliation,
    complete_reconciliation,
    create_consent_receipt,
    delete_source_records,
    fetch_events_for_window,
    fuse_baseline_evidence,
    fuse_events,
    persist_batch,
    reconcile_source_records,
    upsert_device,
    upsert_device_capabilities,
    upsert_sync_cursor,
    withdraw_consent,
)
from app.services.sensors.persistence_service import as_utc

router = APIRouter(prefix="/api/v1/member2", tags=["Member 2 - Sensor Intelligence"])


@router.get("/claims", response_model=list[FeatureClaim])
async def get_claim_boundaries(
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[FeatureClaim]:
    """Expose machine-readable promotion gates and prohibited medical claims."""

    return list(CLAIM_REGISTRY)


@router.post("/consents", response_model=ConsentReceiptResponse, status_code=status.HTTP_201_CREATED)
async def record_consent_receipt(
    receipt: ConsentReceiptCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentReceiptResponse:
    try:
        return await create_consent_receipt(db, user.user_id, receipt)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/consents/{receipt_id}/withdraw", response_model=ConsentWithdrawalResponse)
async def withdraw_consent_receipt(
    receipt_id: UUID,
    request: ConsentWithdrawalRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentWithdrawalResponse:
    try:
        return await withdraw_consent(db, user.user_id, receipt_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/events/batch", response_model=HealthEventBatchResponse)
async def ingest_event_batch(
    batch: HealthEventBatchCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HealthEventBatchResponse:
    try:
        return await persist_batch(db, batch, user.user_id, datetime.now(UTC))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/features/align", response_model=MultimodalFusionResponse)
async def align_persisted_features(
    request: MultimodalFusionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MultimodalFusionResponse:
    events = await fetch_events_for_window(
        db,
        user.user_id,
        request.requested_metrics,
        request.window_start,
        request.window_end,
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return MultimodalFusionResponse(vector=vector)


@router.post("/evidence/fuse", response_model=MultimodalEvidenceVector)
async def fuse_authenticated_evidence(
    request: MultimodalEvidenceRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> MultimodalEvidenceVector:
    if request.vector.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="vector does not belong to token subject",
        )
    return fuse_baseline_evidence(request)


@router.post("/quality/record-integrity", response_model=QualityAssessmentResponse)
async def assess_authenticated_record(
    request: RecordIntegrityAssessmentRequest,
    _: AuthenticatedUser = Depends(get_current_user),
) -> QualityAssessmentResponse:
    try:
        return assess_record_integrity(request.reading, request.received_at)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/quality/waveform", response_model=WaveformQualityResponse)
async def assess_authenticated_waveform(
    request: WaveformQualityAssessmentRequest,
    _: AuthenticatedUser = Depends(get_current_user),
) -> WaveformQualityResponse:
    return assess_waveform_quality(request)


@router.post("/camera/quality", response_model=CameraFrameQualityResponse)
async def assess_authenticated_camera_frame(
    request: CameraFrameQualityRequest,
    _: AuthenticatedUser = Depends(get_current_user),
) -> CameraFrameQualityResponse:
    return assess_camera_frame_quality(request)


@router.put("/devices", response_model=DeviceRegistrationResponse)
async def register_or_update_device(
    request: DeviceRegistrationRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceRegistrationResponse:
    row = await upsert_device(db, user.user_id, request.device)
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
async def register_device_capabilities(
    request: DeviceCapabilityUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceCapabilityBatchResponse:
    try:
        return await upsert_device_capabilities(db, user.user_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.put("/sync/cursor", response_model=HealthConnectSyncCursorResponse)
async def save_sync_cursor(
    cursor: HealthConnectSyncCursor,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HealthConnectSyncCursorResponse:
    row = await upsert_sync_cursor(db, user.user_id, cursor)
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
async def apply_source_deletions(
    request: SourceDeletionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceDeletionResponse:
    deleted = await delete_source_records(db, user.user_id, request)
    return SourceDeletionResponse(
        requested_count=len(request.source_record_ids),
        deleted_count=deleted,
        tombstoned_count=len(request.source_record_ids),
    )


@router.post("/sync/reconcile", response_model=SourceReconciliationResponse)
async def reconcile_expired_token_snapshot(
    request: SourceReconciliationRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceReconciliationResponse:
    deleted = await reconcile_source_records(db, user.user_id, request)
    return SourceReconciliationResponse(
        authoritative_count=len(request.source_record_ids),
        deleted_stale_count=deleted,
    )


@router.post(
    "/sync/reconcile/sessions",
    response_model=ReconciliationSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reconciliation_session(
    request: ReconciliationSessionCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationSessionResponse:
    try:
        return await begin_reconciliation(db, user.user_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post(
    "/sync/reconcile/sessions/{session_id}/records",
    response_model=ReconciliationChunkResponse,
)
async def append_reconciliation_records(
    session_id: UUID,
    request: ReconciliationRecordChunk,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationChunkResponse:
    try:
        return await add_reconciliation_records(db, user.user_id, session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post(
    "/sync/reconcile/sessions/{session_id}/complete",
    response_model=ReconciliationCompleteResponse,
)
async def finish_reconciliation_session(
    session_id: UUID,
    request: ReconciliationCompleteRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationCompleteResponse:
    del request  # Pydantic enforces explicit complete_snapshot=true before this point.
    try:
        return await complete_reconciliation(db, user.user_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
