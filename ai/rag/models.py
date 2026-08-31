"""Immutable knowledge-document models for the Member 3 RAG pipeline.

All stored knowledge chunks must carry explicit review metadata.
Only ``approved`` and non-expired chunks may be retrieved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class ReviewStatus(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"
    EXPIRED = "expired"


def _require_nonempty(value: str, label: str) -> str:
    """Strip and reject blank strings."""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{label} must not be empty or whitespace-only")
    return stripped


def _normalise_string_collection(values: Sequence[str], label: str) -> tuple[str, ...]:
    """Validate and strip collection of strings; reject strings or malformed collections."""
    if isinstance(values, str) or not isinstance(values, (tuple, list)):
        raise ValueError(
            f"{label} must be a list or tuple of non-blank strings, not {type(values).__name__}"
        )
    if not values:
        raise ValueError(f"{label} must contain at least one non-blank string")
    normalised = []
    for idx, item in enumerate(values):
        if not isinstance(item, str):
            raise ValueError(
                f"Every item in {label} must be a string, got {type(item).__name__} at index {idx}"
            )
        stripped = item.strip()
        if not stripped:
            raise ValueError(
                f"Items in {label} must not be empty or whitespace-only (index {idx})"
            )
        normalised.append(stripped)
    return tuple(normalised)


@dataclass(frozen=True)
class KnowledgeChunk:
    """A single retrieved passage from the approved knowledge base.

    All string identifiers are stripped and validated at construction.
    Only chunks with ``review_status == ReviewStatus.APPROVED`` and
    ``expires_on`` either absent or in the future may be returned by the
    retriever.
    """

    document_id: str
    chunk_id: str
    title: str
    content: str
    source_name: str
    topic: str
    language: str
    reviewed_at: date
    review_status: ReviewStatus
    safety_tags: tuple[str, ...]
    keywords: tuple[str, ...]
    version: str
    source_url: Optional[str] = None
    expires_on: Optional[date] = None

    def __post_init__(self) -> None:
        for label, value in (
            ("document_id", self.document_id),
            ("chunk_id", self.chunk_id),
            ("title", self.title),
            ("content", self.content),
            ("source_name", self.source_name),
            ("topic", self.topic),
            ("language", self.language),
            ("version", self.version),
        ):
            object.__setattr__(self, label, _require_nonempty(value, label))

        object.__setattr__(
            self,
            "safety_tags",
            _normalise_string_collection(self.safety_tags, "safety_tags"),
        )
        object.__setattr__(
            self,
            "keywords",
            tuple(
                value.lower()
                for value in _normalise_string_collection(self.keywords, "keywords")
            ),
        )
        if self.source_url is not None:
            object.__setattr__(
                self,
                "source_url",
                _require_nonempty(self.source_url, "source_url"),
            )

    def is_usable(self, today: Optional[date] = None) -> bool:
        """Return True only if status is approved and not expired."""
        if self.review_status != ReviewStatus.APPROVED:
            return False
        if self.expires_on is not None:
            check_date = today or date.today()
            if check_date > self.expires_on:
                return False
        return True
