"""Single-entry Member 3 Guardian orchestration API."""

from fastapi import APIRouter, Depends

from app.schemas.member3.guardian import GuardianProcessRequest, GuardianProcessResponse
from app.services.member3.guardian.orchestration_service import GuardianOrchestrationService

router = APIRouter(prefix="/api/v1/member3/guardian", tags=["Member 3 - Guardian"])
_service = GuardianOrchestrationService()


def get_guardian_service() -> GuardianOrchestrationService:
    return _service


@router.post("/process", response_model=GuardianProcessResponse)
async def process_guardian_event(
    request: GuardianProcessRequest,
    service: GuardianOrchestrationService = Depends(get_guardian_service),
) -> GuardianProcessResponse:
    return service.process(request)
