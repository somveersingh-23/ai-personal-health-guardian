"""Member 3 caregiver consent API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.member3.caregivers import CaregiverDecisionRequest, CaregiverLink, CaregiverLinkCreate, CaregiverListResponse
from app.services.member3.guardian.caregiver_service import CaregiverAuthorizationError, CaregiverLinkNotFoundError, CaregiverService, InvalidCaregiverTransitionError

router = APIRouter(prefix="/api/v1/member3/caregivers", tags=["Member 3 - Caregivers"])
_service = CaregiverService()
def get_caregiver_service() -> CaregiverService: return _service

@router.post("", response_model=CaregiverLink)
async def create_link(request: CaregiverLinkCreate, service: CaregiverService = Depends(get_caregiver_service)) -> CaregiverLink:
    try: return service.create(request)
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post("/{link_id}/decisions", response_model=CaregiverLink)
async def decide(link_id: str, request: CaregiverDecisionRequest, service: CaregiverService = Depends(get_caregiver_service)) -> CaregiverLink:
    try: return service.decide(link_id, request)
    except CaregiverLinkNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CaregiverAuthorizationError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidCaregiverTransitionError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("", response_model=CaregiverListResponse)
async def list_links(user_id: str = Query(min_length=1), service: CaregiverService = Depends(get_caregiver_service)) -> CaregiverListResponse:
    return service.list_for_user(user_id)
