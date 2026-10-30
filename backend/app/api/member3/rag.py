"""API router for Member 3 RAG retrieval and document ingestion endpoints.

Do NOT register this router in main.py directly.
See docs/api/member3/rag-api.md for the integration snippet.

Endpoints:
    POST   /api/v1/member3/rag/retrieve
    POST   /api/v1/member3/rag/ingest/text
    DELETE /api/v1/member3/rag/documents/{document_id}
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.member3.rag import (
    DocumentDeleteResponse,
    DocumentIngestResponse,
    DocumentIngestTextRequest,
    RetrievalRequest,
    RetrievalResponse,
)
from app.services.member3.guardian.retrieval_service import (
    DocumentDeletionError,
    DocumentIngestionError,
    InvalidRetrievalRequestError,
    MalformedKnowledgeBaseError,
    RetrievalFailureError,
    RetrievalService,
)


def _resolve_default_kb_path() -> Path:
    """Robustly resolve the default knowledge-base file path from repo root."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        candidate = parent / "ai" / "knowledge_base" / "member3" / "health_topics.jsonl"
        if candidate.is_file():
            return candidate
    return current.parents[4] / "ai" / "knowledge_base" / "member3" / "health_topics.jsonl"


_DEFAULT_KB_PATH = _resolve_default_kb_path()

router = APIRouter(
    prefix="/api/v1/member3/rag",
    tags=["Member 3 - RAG"],
)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_retrieval_service() -> RetrievalService:
    """Provide a default RetrievalService using the bundled knowledge base.

    Override this dependency in tests to inject a custom knowledge base.
    """
    return RetrievalService(knowledge_base_paths=[_resolve_default_kb_path()])


# ---------------------------------------------------------------------------
# Endpoints
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


@router.post(
    "/ingest/text",
    response_model=DocumentIngestResponse,
    summary="Ingest medical document text into knowledge base",
    description=(
        "Sanitizes, chunks, hashes, and indexes medical document text. "
        "Neutralizes prompt injection attempts and removes control characters. "
        "Enforces 5MB size limit."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def ingest_text(
    request: DocumentIngestTextRequest,
    service: RetrievalService = Depends(get_retrieval_service),
) -> DocumentIngestResponse:
    """Ingest medical document text into the knowledge base."""
    try:
        return service.ingest_text(request)

    except DocumentIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest document text. Please try again.",
        )


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete document from knowledge base",
    description="Removes all chunks for document_id and re-indexes the retriever.",
    status_code=status.HTTP_200_OK,
)
async def delete_document(
    document_id: str,
    service: RetrievalService = Depends(get_retrieval_service),
) -> DocumentDeleteResponse:
    """Delete a document and its chunks by document_id."""
    clean_id = document_id.strip()
    if not clean_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document_id must not be empty or whitespace-only",
        )

    try:
        response = service.delete_document(clean_id)
        if response.chunks_deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{clean_id}' not found in knowledge base.",
            )
        return response

    except HTTPException:
        raise

    except DocumentDeletionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document. Please try again.",
        )
