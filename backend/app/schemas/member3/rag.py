"""Pydantic schemas for the Member 3 RAG retrieval API.

Validation rules:
- question: stripped, non-empty
- locale: validated against SUPPORTED_LOCALES; falls back to 'en'
- top_k: integer in [1, 10]
- score: finite float
- result_count: must match len(results)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.member3.assistant import SUPPORTED_LOCALES

_LOCALE_FALLBACK = "en"
_MIN_TOP_K = 1
_MAX_TOP_K = 10


class RetrievalRequest(BaseModel):
    """Request body for POST /api/v1/member3/rag/retrieve."""

    question: Annotated[str, Field(min_length=1, description="Sanitized health question")]
    topics: Optional[list[str]] = Field(
        default=None,
        description="Optional topic filter; each must be a non-blank string",
    )
    locale: str = Field(default=_LOCALE_FALLBACK, description="BCP-47 locale; falls back to 'en'")
    top_k: int = Field(
        default=3,
        ge=_MIN_TOP_K,
        le=_MAX_TOP_K,
        description=f"Maximum results ({_MIN_TOP_K}–{_MAX_TOP_K})",
    )

    @field_validator("question", mode="before")
    @classmethod
    def _strip_and_reject_blank_question(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("question must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be empty or whitespace-only")
        return stripped

    @field_validator("topics", mode="before")
    @classmethod
    def _validate_topics(cls, value):
        if value is None:
            return value
        if not isinstance(value, list):
            raise ValueError("topics must be a list")
        result = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("each topic must be a string")
            stripped = item.strip()
            if not stripped:
                raise ValueError("topic strings must not be blank")
            result.append(stripped.lower())
        return result

    @field_validator("locale", mode="before")
    @classmethod
    def _normalise_locale(cls, value: str) -> str:
        if not isinstance(value, str):
            return _LOCALE_FALLBACK
        normalised = value.strip()
        return normalised if normalised in SUPPORTED_LOCALES else _LOCALE_FALLBACK

    model_config = {"frozen": True}


class RetrievalResult(BaseModel):
    """A single retrieved passage with source metadata."""

    document_id: str
    chunk_id: str
    title: str
    passage: str
    topic: str
    source_name: str
    source_url: Optional[str] = None
    reviewed_at: str
    score: float = Field(ge=0)

    @field_validator("score", mode="before")
    @classmethod
    def _validate_score(cls, value: float) -> float:
        if isinstance(value, bool):
            raise ValueError("score must be a finite non-negative number")
        if not isinstance(value, (int, float)):
            raise ValueError("score must be a finite non-negative number")
        val = float(value)
        if not math.isfinite(val):
            raise ValueError("score must be a finite number")
        if val < 0.0:
            raise ValueError("score must be non-negative")
        return val

    @field_validator("document_id", "chunk_id", "title", "passage", "topic", "source_name", "reviewed_at", mode="before")
    @classmethod
    def _strip_and_reject_blank(cls, value: str, info) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} must not be blank")
        return stripped

    model_config = {"frozen": True}


class RetrievalResponse(BaseModel):
    """Response body for POST /api/v1/member3/rag/retrieve."""

    query: str
    results: list[RetrievalResult]
    result_count: int
    limitations: list[str]
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    @model_validator(mode="after")
    def _check_result_count(self) -> "RetrievalResponse":
        if self.result_count != len(self.results):
            raise ValueError(
                f"result_count ({self.result_count}) does not match "
                f"len(results) ({len(self.results)})"
            )
        return self


# ---------------------------------------------------------------------------
# Document Ingestion Schemas
# ---------------------------------------------------------------------------

_MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


class DocumentIngestTextRequest(BaseModel):
    """Request body for POST /api/v1/member3/rag/ingest/text."""

    document_id: Annotated[str, Field(min_length=1, description="Unique identifier for the document")]
    title: Annotated[str, Field(min_length=1, description="Human-readable title for the document")]
    text: Annotated[str, Field(min_length=1, description="Medical text content to ingest")]
    topic: str = Field(default="general_health", description="Health topic category")
    source_name: str = Field(
        default="Authorized Medical Ingestion",
        description="Name of the authoritative source or guidelines",
    )
    source_url: Optional[str] = Field(default=None, description="Optional canonical URL")
    language: str = Field(default=_LOCALE_FALLBACK, description="BCP-47 language code")
    version: str = Field(default="1.0", description="Document revision version")
    safety_tags: Optional[list[str]] = Field(
        default=None,
        description="Safety classification tags (e.g. non_diagnostic, educational)",
    )
    keywords: Optional[list[str]] = Field(
        default=None,
        description="Optional list of keywords to associate with chunks",
    )
    chunk_size: int = Field(default=600, ge=50, le=5000, description="Max characters per chunk")
    chunk_overlap: int = Field(default=100, ge=0, le=1000, description="Overlap characters between chunks")
    min_chunk_size: int = Field(default=50, ge=1, le=500, description="Minimum characters for a valid chunk")

    @field_validator("document_id", "title", "text", "topic", "source_name", "language", "version", mode="before")
    @classmethod
    def _strip_and_reject_blank_fields(cls, value: str, info) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} must not be empty or whitespace-only")
        return stripped

    @field_validator("text")
    @classmethod
    def _validate_text_size_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > _MAX_DOCUMENT_SIZE_BYTES:
            raise ValueError(
                f"Document text exceeds maximum size limit of {_MAX_DOCUMENT_SIZE_BYTES} bytes (5MB)"
            )
        return value

    @field_validator("safety_tags", "keywords", mode="before")
    @classmethod
    def _validate_string_array(cls, value, info):
        if value is None:
            return value
        if not isinstance(value, list):
            raise ValueError(f"{info.field_name} must be a list of non-blank strings")
        cleaned = []
        for idx, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    f"{info.field_name} items must be non-blank strings, invalid at index {idx}"
                )
            cleaned.append(item.strip())
        if not cleaned:
            raise ValueError(f"{info.field_name} must contain at least one non-blank string")
        return cleaned

    @model_validator(mode="after")
    def _validate_chunking_constraints(self) -> "DocumentIngestTextRequest":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")
        if self.min_chunk_size > self.chunk_size:
            raise ValueError("min_chunk_size cannot exceed chunk_size")
        return self

    model_config = {"frozen": True}


class IngestedChunkInfo(BaseModel):
    """Metadata summary of an ingested chunk."""

    chunk_id: str
    document_id: str
    title: str
    content_hash: str
    char_count: int
    keywords: list[str]
    topic: str

    model_config = {"frozen": True}


class DocumentIngestResponse(BaseModel):
    """Response body for document ingestion."""

    document_id: str
    title: str
    chunks_created: int
    chunks: list[IngestedChunkInfo]
    injection_detected: bool
    sanitized: bool
    total_chars: int
    reindexed: bool
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    model_config = {"frozen": True}


class DocumentDeleteResponse(BaseModel):
    """Response body for DELETE /api/v1/member3/rag/documents/{document_id}."""

    document_id: str
    chunks_deleted: int
    reindexed: bool
    deleted_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    model_config = {"frozen": True}
