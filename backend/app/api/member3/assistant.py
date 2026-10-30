"""API router for the Member 3 AI Guardian assistant.

Endpoint
--------
POST /api/v1/member3/assistant/explain

The router is **not** registered in ``main.py`` by this file.  See the
integration snippet in ``docs/api/member3/assistant-api.md``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.member3.assistant import ExplainRequest, ExplainResponse
from app.services.member3.guardian.explanation_service import (
    ExplanationService,
    InsufficientEvidenceError,
    ProviderError,
    UnsupportedActionError,
)

router = APIRouter(
    prefix="/api/v1/member3/assistant",
    tags=["Member 3 - AI Guardian"],
)


# ---------------------------------------------------------------------------
# Dependency providers
# ---------------------------------------------------------------------------

def get_explanation_service() -> ExplanationService:
    """FastAPI dependency that provides a default ``ExplanationService``.

    Swap the provider here (or override the dependency in tests) to use
    a real LLM backend without changing the router or service code.
    """
    return ExplanationService()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Generate a safe health explanation from structured evidence",
    description=(
        "Accepts structured health evidence and a pre-computed SafetyDecision. "
        "Returns a calm, evidence-grounded explanation that never diagnoses, "
        "never invents measurements, and never changes the safety action."
    ),
    status_code=status.HTTP_200_OK,
)
async def explain(
    request: ExplainRequest,
    service: ExplanationService = Depends(get_explanation_service),
) -> ExplainResponse:
    """Generate a safe AI Guardian explanation.

    Returns
    -------
    ExplainResponse
        The generated explanation with the safety action echoed unchanged.

    Raises
    ------
    422 Unprocessable Entity
        - Invalid or empty ``question`` (Pydantic validation).
        - Confidence or signal quality out of [0, 1] or non-finite.
        - Empty ``evidence`` list.
        - Unrecognised ``safety_action`` value.
        - No usable evidence after normalisation.
    500 Internal Server Error
        - Assistant provider failure.
    """
    try:
        return service.explain(request)

    except UnsupportedActionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except InsufficientEvidenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The assistant provider failed to generate a response. Please try again.",
        ) from exc
