"""Retrieval service for the Member 3 RAG pipeline.

Bridges the API layer to the local keyword retriever and ingestion pipeline.
Enforces passage-length and total-context limits.
Never changes the incoming safety action.
Never exposes absolute filesystem paths or stack traces.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from ai.rag.ingestion import (
    IngestionError,
    MedicalDocumentIngestor,
    delete_document_from_jsonl,
)
from ai.rag.loader import KnowledgeBaseLoader, LoaderError
from ai.rag.retriever import LocalKeywordRetriever, RetrievalRecord
from app.schemas.member3.rag import (
    DocumentDeleteResponse,
    DocumentIngestResponse,
    DocumentIngestTextRequest,
    IngestedChunkInfo,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
)

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

class DocumentIngestionError(RetrievalServiceError):
    """Raised when document ingestion fails."""

class DocumentDeletionError(RetrievalServiceError):
    """Raised when document deletion fails."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class RetrievalService:
    """Orchestrate knowledge-base loading, retrieval, ingestion, and reindexing.

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
        if (
            isinstance(max_passage_chars, bool)
            or not isinstance(max_passage_chars, int)
            or max_passage_chars < 2
        ):
            raise ValueError("max_passage_chars must be an integer of at least 2")
        if (
            isinstance(max_total_chars, bool)
            or not isinstance(max_total_chars, int)
            or max_total_chars < 1
        ):
            raise ValueError("max_total_chars must be a positive integer")
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

    def reindex(self) -> int:
        """Clear cached retriever and reload all chunks from storage.

        Returns the number of approved, usable chunks indexed.
        """
        self._retriever = None
        retriever = self._get_retriever()
        return len(retriever._chunks)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """Run retrieval and return structured results.

        Returns a response with an empty results list when nothing is
        relevant — never raises an error for a zero-result query.
        """
        retriever = self._get_retriever()

        try:
            raw_records: list[RetrievalRecord] = retriever.retrieve(
                query=request.question,
                top_k=request.top_k,
                topic_filter=request.topics,
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

    def ingest_text(
        self,
        request: DocumentIngestTextRequest,
        kb_path: Optional[str | Path] = None,
    ) -> DocumentIngestResponse:
        """Ingest document text into the knowledge base, then re-index retriever."""
        target_path = Path(kb_path) if kb_path is not None else Path(self._kb_paths[0])
        try:
            ingestor = MedicalDocumentIngestor(
                kb_path=target_path,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                min_chunk_size=request.min_chunk_size,
            )
            ingested_doc = ingestor.ingest_text(
                text=request.text,
                document_id=request.document_id,
                title=request.title,
                topic=request.topic,
                source_name=request.source_name,
                source_url=request.source_url,
                language=request.language,
                version=request.version,
                safety_tags=tuple(request.safety_tags) if request.safety_tags else None,
                keywords=tuple(request.keywords) if request.keywords else None,
            )
            # Reindex retriever so chunks are immediately accessible
            self.reindex()
        except (ValueError, IngestionError) as exc:
            raise DocumentIngestionError(str(exc)) from exc
        except Exception as exc:
            raise DocumentIngestionError(
                "Failed to ingest document text due to an unexpected error."
            ) from exc

        chunk_summaries = [
            IngestedChunkInfo(
                chunk_id=c.chunk.chunk_id,
                document_id=c.chunk.document_id,
                title=c.chunk.title,
                content_hash=c.content_hash,
                char_count=c.char_count,
                keywords=list(c.chunk.keywords),
                topic=c.chunk.topic,
            )
            for c in ingested_doc.chunks
        ]

        return DocumentIngestResponse(
            document_id=ingested_doc.document_id,
            title=ingested_doc.title,
            chunks_created=len(ingested_doc.chunks),
            chunks=chunk_summaries,
            injection_detected=ingested_doc.injection_detected,
            sanitized=ingested_doc.sanitized,
            total_chars=ingested_doc.total_chars,
            reindexed=True,
            created_at=datetime.now(tz=timezone.utc),
        )

    def delete_document(
        self,
        document_id: str,
        kb_path: Optional[str | Path] = None,
    ) -> DocumentDeleteResponse:
        """Delete all chunks for a document_id and re-index the retriever."""
        target_id = document_id.strip()
        if not target_id:
            raise ValueError("document_id must not be empty or whitespace-only")

        try:
            if kb_path is not None:
                deleted_count = delete_document_from_jsonl(Path(kb_path), target_id)
            else:
                deleted_count = 0
                for path in self._kb_paths:
                    deleted_count += delete_document_from_jsonl(Path(path), target_id)

            # Reindex retriever
            self.reindex()
        except Exception as exc:
            raise DocumentDeletionError(
                f"Failed to delete document '{target_id}'."
            ) from exc

        return DocumentDeleteResponse(
            document_id=target_id,
            chunks_deleted=deleted_count,
            reindexed=True,
            deleted_at=datetime.now(tz=timezone.utc),
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
                passage = passage[: self._max_passage_chars - 1] + "…"
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
