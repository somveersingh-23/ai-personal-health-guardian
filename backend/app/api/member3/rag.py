"""API router for the Member 3 RAG retrieval endpoint.

Do NOT register this router in main.py directly.
See docs/api/member3/rag-api.md for the integration snippet.

Endpoint:
    POST /api/v1/member3/rag/retrieve
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.member3.rag import RetrievalRequest, RetrievalResponse
from app.services.member3.guardian.retrieval_service import (
    InvalidRetrievalRequestError,
    MalformedKnowledgeBaseError,
    RetrievalFailureError,
    RetrievalService,
)

# Default knowledge-base path (relative to the project root)
_DEFAULT_KB_PATH = (
    Path(__file__).parent.parent.parent.parent.parent.parent
    / "ai" / "knowledge_base" / "member3" / "health_topics.jsonl"
)

router = APIRouter(
    prefix="/api/v1/member3/rag",
    tags=["Member 3 - RAG Retrieval"],
)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_retrieval_service() -> RetrievalService:
    """Provide a default RetrievalService using the bundled knowledge base.

    Override this dependency in tests to inject a custom knowledge base.
    """
    return RetrievalService(knowledge_base_paths=[_DEFAULT_KB_PATH])


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/retrieve",
    response_model=RetrievalResponse,
    summary="Retrieve relevant health-information passages",
    description=(
        "Returns top-k relevant passages from the approved local knowledge base. "
        "Retrieval is keyword-based and entirely offline. "
        "Retrieved content is educational only and never replaces medical advice."
    ),
    status_code=status.HTTP_200_OK,
)
async def retrieve(
    request: RetrievalRequest,
    service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponse:
    """Retrieve relevant knowledge-base passages for a health question.

    Returns 200 even when no relevant passages are found (empty results list).
    """
    try:
        return service.retrieve(request)

    except MalformedKnowledgeBaseError:
        # Never expose internal paths or stack traces
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge base is unavailable. Contact server administrator.",
        )

    except InvalidRetrievalRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except RetrievalFailureError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Retrieval failed. Please try again.",
        )
