"""Member 3 emergency-workflow API; no external emergency connector is called."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.schemas.member3.emergency import (
    EmergencyCommandRequest,
    EmergencyListResponse,
    EmergencyStartRequest,
    EmergencyWorkflowRecord,
)
from app.services.member3.guardian.emergency_service import (
    EmergencyWorkflowNotFoundError,
    EmergencyWorkflowService,
    InvalidEmergencyTransitionError,
    MissingCaregiverContactError,
)
from app.core.member3.security import member3_identity_if_authenticated

router = APIRouter(prefix="/api/v1/member3/emergency", tags=["Member 3 - Emergency"])
_service = EmergencyWorkflowService()


def get_emergency_service() -> EmergencyWorkflowService:
    return _service


@router.post("/workflows", response_model=EmergencyWorkflowRecord)
async def start_workflow(
    request: EmergencyStartRequest,
    service: EmergencyWorkflowService = Depends(get_emergency_service),
) -> EmergencyWorkflowRecord:
    return service.start(request)


@router.post("/workflows/{workflow_id}/commands", response_model=EmergencyWorkflowRecord)
async def apply_command(
    workflow_id: str,
    request: EmergencyCommandRequest,
    http_request: Request,
    service: EmergencyWorkflowService = Depends(get_emergency_service),
) -> EmergencyWorkflowRecord:
    try:
        identity = member3_identity_if_authenticated(http_request)
        return service.command(workflow_id, request, identity.user_id if identity else None)
    except EmergencyWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidEmergencyTransitionError, MissingCaregiverContactError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/workflows/{workflow_id}", response_model=EmergencyWorkflowRecord)
async def get_workflow(
    workflow_id: str,
    request: Request,
    service: EmergencyWorkflowService = Depends(get_emergency_service),
) -> EmergencyWorkflowRecord:
    try:
        identity = member3_identity_if_authenticated(request)
        return service.get_for_user(workflow_id, identity.user_id) if identity else service.get(workflow_id)
    except EmergencyWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/workflows", response_model=EmergencyListResponse)
async def list_workflows(
    user_id: str = Query(min_length=1, max_length=128),
    service: EmergencyWorkflowService = Depends(get_emergency_service),
) -> EmergencyListResponse:
    try:
        return service.list_workflows(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
