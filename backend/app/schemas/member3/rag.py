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
            raise ValueError("score must be a finite number")
        if not isinstance(value, (int, float)):
            raise ValueError("score must be a finite number")
        if not math.isfinite(float(value)):
            raise ValueError("score must be a finite number")
        return float(value)

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
