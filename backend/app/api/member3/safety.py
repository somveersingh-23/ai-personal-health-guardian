"""Member 3 deterministic safety API."""

from fastapi import APIRouter, Depends

from app.schemas.member3.safety import SafetyEvaluationRequest, SafetyEvaluationResponse
from app.services.member3.guardian.safety_service import SafetyEvaluationService

router = APIRouter(prefix="/api/v1/member3/safety", tags=["Member 3 - Safety"])
_service = SafetyEvaluationService()


def get_safety_service() -> SafetyEvaluationService:
    return _service


@router.post("/evaluate", response_model=SafetyEvaluationResponse)
async def evaluate_safety(
    request: SafetyEvaluationRequest,
    service: SafetyEvaluationService = Depends(get_safety_service),
) -> SafetyEvaluationResponse:
    return service.evaluate(request)
