"""Retrieval service for the Member 3 RAG pipeline.

Bridges the API layer to the local keyword retriever.
Enforces passage-length and total-context limits.
Never changes the incoming safety action.
Never exposes absolute filesystem paths or stack traces.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from ai.rag.loader import KnowledgeBaseLoader, LoaderError
from ai.rag.retriever import LocalKeywordRetriever, RetrievalRecord
from app.schemas.member3.rag import RetrievalRequest, RetrievalResponse, RetrievalResult

# Safety limits
_MAX_PASSAGE_CHARS = 800
_MAX_TOTAL_CONTEXT_CHARS = 3000

_STANDARD_LIMITATION = (
    "Retrieved passages are educational reference content only. "
    "They are not medical advice, diagnosis, or treatment guidance. "
    "Always consult a qualified healthcare professional."
)


# ---------------------------------------------------------------------------
# Service exceptions
# ---------------------------------------------------------------------------

class RetrievalServiceError(RuntimeError):
    """Base exception for retrieval service failures."""

class MalformedKnowledgeBaseError(RetrievalServiceError):
    """Raised when the knowledge base cannot be loaded."""

class InvalidRetrievalRequestError(RetrievalServiceError):
    """Raised when the retrieval request is invalid."""

class RetrievalFailureError(RetrievalServiceError):
    """Raised when retrieval fails unexpectedly."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class RetrievalService:
    """Orchestrate knowledge-base loading and retrieval.

    Parameters
    ----------
    knowledge_base_paths:
        Paths to JSON/JSONL knowledge-base files.
    max_passage_chars:
        Maximum characters per retrieved passage (truncated if longer).
    max_total_chars:
        Maximum total characters across all returned passages.
    """

    def __init__(
        self,
        knowledge_base_paths: Sequence[str | Path],
        max_passage_chars: int = _MAX_PASSAGE_CHARS,
        max_total_chars: int = _MAX_TOTAL_CONTEXT_CHARS,
    ) -> None:
        self._kb_paths = list(knowledge_base_paths)
        self._max_passage_chars = max_passage_chars
        self._max_total_chars = max_total_chars
        self._retriever: Optional[LocalKeywordRetriever] = None

    def _get_retriever(self) -> LocalKeywordRetriever:
        """Lazy-load and cache the retriever."""
        if self._retriever is None:
            try:
                loader = KnowledgeBaseLoader(self._kb_paths)
                chunks = loader.load()
            except LoaderError as exc:
                # Never expose internal paths in the error message
                raise MalformedKnowledgeBaseError(
                    "Failed to load knowledge base. Check server configuration."
                ) from exc
            self._retriever = LocalKeywordRetriever(chunks)
        return self._retriever

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """Run retrieval and return structured results.

        Returns a response with an empty results list when nothing is
        relevant — never raises an error for a zero-result query.
        """
        retriever = self._get_retriever()

        try:
            topic_filter = request.topics[0] if request.topics else None
            raw_records: list[RetrievalRecord] = retriever.retrieve(
                query=request.question,
                top_k=request.top_k,
                topic_filter=topic_filter,
            )
        except ValueError as exc:
            raise InvalidRetrievalRequestError(str(exc)) from exc
        except Exception as exc:
            raise RetrievalFailureError(
                "Retrieval encountered an unexpected error."
            ) from exc

        results, limitations = self._build_results(raw_records)
        if not limitations:
            limitations = [_STANDARD_LIMITATION]
        elif _STANDARD_LIMITATION not in limitations:
            limitations.insert(0, _STANDARD_LIMITATION)

        return RetrievalResponse(
            query=request.question,
            results=results,
            result_count=len(results),
            limitations=limitations,
            generated_at=datetime.now(tz=timezone.utc),
        )

    def _build_results(
        self, records: list[RetrievalRecord]
    ) -> tuple[list[RetrievalResult], list[str]]:
        """Convert records to schema objects, enforcing length limits."""
        results: list[RetrievalResult] = []
        limitations: list[str] = []
        total_chars = 0

        for record in records:
            passage = record.sanitized_content

            # Enforce per-passage limit
            if len(passage) > self._max_passage_chars:
                passage = passage[: self._max_passage_chars] + "…"
                limitations.append(
                    f"Passage for '{record.chunk.title}' was truncated to "
                    f"{self._max_passage_chars} characters."
                )

            # Enforce total-context limit
            if total_chars + len(passage) > self._max_total_chars:
                break
            total_chars += len(passage)

            if record.injection_flagged:
                limitations.append(
                    f"Content in '{record.chunk.title}' contained suspicious "
                    "patterns and was partially sanitized."
                )

            results.append(
                RetrievalResult(
                    document_id=record.chunk.document_id,
                    chunk_id=record.chunk.chunk_id,
                    title=record.chunk.title,
                    passage=passage,
                    topic=record.chunk.topic,
                    source_name=record.chunk.source_name,
                    source_url=record.chunk.source_url,
                    reviewed_at=record.chunk.reviewed_at.isoformat(),
                    score=record.score,
                )
            )

        return results, limitations
