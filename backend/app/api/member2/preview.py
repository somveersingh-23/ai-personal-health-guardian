"""Development-only stateless preview routes for Member 2 algorithms."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.member2 import (
    CameraFrameQualityRequest,
    CameraFrameQualityResponse,
    HealthEventBatchPreviewRequest,
    HealthEventBatchPreviewResponse,
    HealthEventCreate,
    MultimodalEvidenceRequest,
    MultimodalEvidenceVector,
    MultimodalFusionPreviewRequest,
    MultimodalFusionResponse,
    QualityAssessmentResponse,
    ReadingCreate,
    RecordIntegrityAssessmentRequest,
    WaveformQualityAssessmentRequest,
    WaveformQualityResponse,
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

router = APIRouter(prefix="/api/v1/member2/preview", tags=["Member 2 - Development Preview"])


@router.post("/normalize", response_model=HealthEventCreate)
async def normalize_preview(
    reading: ReadingCreate,
    user_id: int = Query(gt=0, description="Preview-only simulation identifier"),
) -> HealthEventCreate:
    try:
        return normalize_reading(reading, user_id, datetime.now(UTC))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/batch-normalize", response_model=HealthEventBatchPreviewResponse)
async def batch_normalize_preview(
    batch: HealthEventBatchPreviewRequest,
) -> HealthEventBatchPreviewResponse:
    try:
        return normalize_batch_readings(batch, datetime.now(UTC))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/record-integrity", response_model=QualityAssessmentResponse)
async def record_integrity_preview(
    request: RecordIntegrityAssessmentRequest,
) -> QualityAssessmentResponse:
    try:
        return assess_record_integrity(request.reading, request.received_at)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/waveform-quality", response_model=WaveformQualityResponse)
async def waveform_quality_preview(
    request: WaveformQualityAssessmentRequest,
) -> WaveformQualityResponse:
    return assess_waveform_quality(request)


@router.post("/camera-quality", response_model=CameraFrameQualityResponse)
async def camera_quality_preview(
    request: CameraFrameQualityRequest,
) -> CameraFrameQualityResponse:
    return assess_camera_frame_quality(request)


@router.post("/features/align", response_model=MultimodalFusionResponse)
async def feature_alignment_preview(
    request: MultimodalFusionPreviewRequest,
) -> MultimodalFusionResponse:
    try:
        return MultimodalFusionResponse(
            vector=fuse_events(
                request.events,
                request.requested_metrics,
                request.window_start,
                request.window_end,
                request.minimum_integrity_score,
                request.minimum_composite_quality,
                request.minimum_available_metrics,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/evidence/fuse", response_model=MultimodalEvidenceVector)
async def evidence_fusion_preview(request: MultimodalEvidenceRequest) -> MultimodalEvidenceVector:
    return fuse_baseline_evidence(request)


@router.get("/simulator/feed", response_model=list[ReadingCreate])
async def simulator_feed(
    user_id: int = Query(1, gt=0, description="Simulation user identifier"),
    start_time: datetime | None = Query(None),
    hours: int = Query(24, ge=1, le=168),
    seed: int = Query(42),
) -> list[ReadingCreate]:
    start = start_time or datetime.now(UTC)
    try:
        return generate_health_feed(user_id, start, hours, seed)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
