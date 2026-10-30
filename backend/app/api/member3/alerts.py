"""Member 3 alert API. Router registration remains a shared integration step."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.schemas.member3.alerts import (
    AlertEvaluationRequest,
    AlertEvaluationResponse,
    AlertListResponse,
    AlertRecord,
    AlertStatusUpdateRequest,
)
from app.services.member3.guardian.alert_service import (
    AlertNotFoundError,
    AlertService,
    InvalidAlertTransitionError,
)
from app.core.member3.security import member3_identity_if_authenticated

router = APIRouter(prefix="/api/v1/member3/alerts", tags=["Member 3 - Alerts"])
_repository_service = AlertService()


def get_alert_service() -> AlertService:
    return _repository_service


@router.post("/evaluate", response_model=AlertEvaluationResponse)
async def evaluate_alert(
    request: AlertEvaluationRequest,
    service: AlertService = Depends(get_alert_service),
) -> AlertEvaluationResponse:
    return service.evaluate(request)


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    user_id: str = Query(min_length=1, max_length=128),
    service: AlertService = Depends(get_alert_service),
) -> AlertListResponse:
    try:
        return service.list_alerts(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch("/{alert_id}/status", response_model=AlertRecord)
async def update_alert_status(
    alert_id: str,
    request: AlertStatusUpdateRequest,
    http_request: Request,
    service: AlertService = Depends(get_alert_service),
) -> AlertRecord:
    try:
        identity = member3_identity_if_authenticated(http_request)
        return (
            service.update_status_for_user(alert_id, identity.user_id, request.status)
            if identity else service.update_status(alert_id, request.status)
        )
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidAlertTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
