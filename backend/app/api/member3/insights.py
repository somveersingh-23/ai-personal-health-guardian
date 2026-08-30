"""Member 3 structured health-insight API."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.member3.insights import (
    InsightCreateRequest,
    InsightListResponse,
    InsightRecord,
    InsightStatusUpdateRequest,
)
from app.services.member3.guardian.insight_service import (
    InsightNotFoundError,
    InsightService,
    InvalidInsightTransitionError,
)

router = APIRouter(prefix="/api/v1/member3/insights", tags=["Member 3 - Insights"])
_service = InsightService()


def get_insight_service() -> InsightService:
    return _service


@router.post("", response_model=InsightRecord)
async def create_insight(
    request: InsightCreateRequest,
    service: InsightService = Depends(get_insight_service),
) -> InsightRecord:
    return service.create(request)


@router.get("", response_model=InsightListResponse)
async def list_insights(
    user_id: str = Query(min_length=1, max_length=128),
    service: InsightService = Depends(get_insight_service),
) -> InsightListResponse:
    try:
        return service.list_insights(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{insight_id}", response_model=InsightRecord)
async def get_insight(
    insight_id: str,
    service: InsightService = Depends(get_insight_service),
) -> InsightRecord:
    try:
        return service.get(insight_id)
    except InsightNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{insight_id}/status", response_model=InsightRecord)
async def update_insight_status(
    insight_id: str,
    request: InsightStatusUpdateRequest,
    service: InsightService = Depends(get_insight_service),
) -> InsightRecord:
    try:
        return service.update_status(insight_id, request.status)
    except InsightNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidInsightTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
