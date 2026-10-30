from fastapi import (
    APIRouter,
    HTTPException,
)

from app.schemas.member1.health_intelligence import (
    DigitalTwinResponse,
    HealthIntelligenceResponse,
)
from app.services.member1.health_intelligence import (
    HealthIntelligenceService,
)


router = APIRouter(
    prefix="/api/member1/health-intelligence",
    tags=[
        "Member 1 - Health Intelligence"
    ],
)


service = (
    HealthIntelligenceService()
)


@router.get(
    "/{user_id}/digital-twin",
    response_model=DigitalTwinResponse,
)
def get_digital_twin(
    user_id: int,
):

    try:

        return service.get_digital_twin(
            user_id
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{user_id}/metrics",
)
def get_digital_twin_metrics(
    user_id: int,
):

    try:

        return {
            "user_id": user_id,
            "metrics": (
                service.get_digital_twin_metrics(
                    user_id
                )
            ),
        }

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{user_id}/insights",
    response_model=HealthIntelligenceResponse,
)
def get_health_insights(
    user_id: int,
):

    try:

        response = (
            service.get_insights(
                user_id
            )
        )

        return response

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{user_id}",
)
def get_health_intelligence(
    user_id: int,
):

    try:

        return (
            service.get_health_intelligence(
                user_id
            )
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc