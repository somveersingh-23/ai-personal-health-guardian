from fastapi import APIRouter, HTTPException

from app.schemas.member1.health_intelligence import (
    DigitalTwinResponse,
    HealthIntelligenceResponse,
)
from app.services.member1.health_intelligence import HealthIntelligenceService

router = APIRouter(
    prefix="/api/member1/health-intelligence",
    tags=["Member 1 - Health Intelligence"],
)
service = HealthIntelligenceService()


def _translate_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="Unable to read health intelligence artifacts")


@router.get("/{user_id}/digital-twin", response_model=DigitalTwinResponse)
def get_digital_twin(user_id: int):
    try:
        return service.get_digital_twin(user_id)
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_errors(exc) from exc


@router.get("/{user_id}/metrics")
def get_digital_twin_metrics(user_id: int):
    try:
        return {"user_id": user_id, "metrics": service.get_digital_twin_metrics(user_id)}
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_errors(exc) from exc


@router.get("/{user_id}/insights", response_model=HealthIntelligenceResponse)
def get_health_insights(user_id: int):
    try:
        return service.get_insights(user_id)
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_errors(exc) from exc


@router.get("/{user_id}")
def get_health_intelligence(user_id: int):
    try:
        return service.get_health_intelligence(user_id)
    except (FileNotFoundError, ValueError) as exc:
        raise _translate_errors(exc) from exc
