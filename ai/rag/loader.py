"""Knowledge-base loader for the Member 3 RAG pipeline.

Loads and validates KnowledgeChunk records from JSON/JSONL files.
Rejects malformed records, duplicates, and non-approved content.
Never uses pickle or unsafe deserialization.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Sequence

from .models import KnowledgeChunk, ReviewStatus


class LoaderError(RuntimeError):
    """Base exception for knowledge-base loading failures."""

class MalformedRecordError(LoaderError):
    """Raised when a record fails validation."""

class DuplicateChunkError(LoaderError):
    """Raised when two records share the same chunk_id."""


_REQUIRED_FIELDS = {
    "document_id", "chunk_id", "title", "content",
    "source_name", "topic", "language", "reviewed_at",
    "review_status", "safety_tags", "keywords", "version",
}


def _normalise_whitespace(text: str) -> str:
    """Collapse internal whitespace runs and strip edges."""
    return re.sub(r"[\s]+", " ", text).strip()


def _parse_chunk(raw: dict, source_hint: str) -> KnowledgeChunk:
    """Parse and validate a raw dict into a KnowledgeChunk.

    Raises MalformedRecordError on any validation failure.
    """
    missing = _REQUIRED_FIELDS - set(raw.keys())
    if missing:
        raise MalformedRecordError(
            f"Record in {source_hint!r} is missing fields: {sorted(missing)}"
        )
    try:
        safety_tags = raw["safety_tags"]
        keywords = raw["keywords"]
        if not isinstance(safety_tags, list):
            raise ValueError("safety_tags must be a JSON array of strings")
        if not isinstance(keywords, list):
            raise ValueError("keywords must be a JSON array of strings")
        if not all(isinstance(value, str) for value in safety_tags):
            raise ValueError("safety_tags must contain only strings")
        if not all(isinstance(value, str) for value in keywords):
            raise ValueError("keywords must contain only strings")

        reviewed_at = date.fromisoformat(raw["reviewed_at"])
        expires_on_raw = raw.get("expires_on")
        expires_on = date.fromisoformat(expires_on_raw) if expires_on_raw else None
        review_status = ReviewStatus(raw["review_status"])

        chunk = KnowledgeChunk(
            document_id=_normalise_whitespace(str(raw["document_id"])),
            chunk_id=_normalise_whitespace(str(raw["chunk_id"])),
            title=_normalise_whitespace(str(raw["title"])),
            content=_normalise_whitespace(str(raw["content"])),
            source_name=_normalise_whitespace(str(raw["source_name"])),
            source_url=raw.get("source_url"),
            topic=_normalise_whitespace(str(raw["topic"])),
            language=_normalise_whitespace(str(raw["language"])),
            reviewed_at=reviewed_at,
            review_status=review_status,
            safety_tags=tuple(safety_tags),
            keywords=tuple(keywords),
            version=_normalise_whitespace(str(raw["version"])),
            expires_on=expires_on,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise MalformedRecordError(
            f"Failed to parse record in {source_hint!r}: {exc}"
        ) from exc
    return chunk


class KnowledgeBaseLoader:
    """Load and validate knowledge chunks from JSON/JSONL files.

    Parameters
    ----------
    paths:
        One or more file paths to load. Each may be a ``.json`` file
        (containing a JSON array) or a ``.jsonl`` file (one JSON object
        per line).  Other extensions raise ``LoaderError``.
    today:
        Override today's date for expiry checks (used in tests).
    """

    def __init__(
        self,
        paths: Sequence[str | Path],
        today: date | None = None,
    ) -> None:
        self._paths = [Path(p) for p in paths]
        self._today = today or date.today()
        self._chunks: list[KnowledgeChunk] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> list[KnowledgeChunk]:
        """Return an immutable, deterministically-ordered list of approved chunks.

        Results are cached after the first call.
        """
        if self._chunks is None:
            self._chunks = self._load_all()
        return list(self._chunks)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_all(self) -> list[KnowledgeChunk]:
        raw_chunks: list[KnowledgeChunk] = []
        seen_chunk_ids: set[str] = set()

        for path in self._paths:
            records = self._read_file(path)
            for raw in records:
                if not isinstance(raw, dict):
                    raise MalformedRecordError(
                        f"Expected a JSON object, got {type(raw).__name__!r} in {path}"
                    )
                chunk = _parse_chunk(raw, str(path))
                if chunk.chunk_id in seen_chunk_ids:
                    raise DuplicateChunkError(
                        f"Duplicate chunk_id {chunk.chunk_id!r} found in {path}"
                    )
                seen_chunk_ids.add(chunk.chunk_id)
                raw_chunks.append(chunk)

        # Filter to approved and non-expired only
        usable = [c for c in raw_chunks if c.is_usable(self._today)]

        # Deterministic ordering: topic → document_id → chunk_id
        usable.sort(key=lambda c: (c.topic, c.document_id, c.chunk_id))
        return usable

    def _read_file(self, path: Path) -> list[dict]:
        """Read JSON or JSONL file; never execute content."""
        if not path.exists():
            raise LoaderError(f"Knowledge-base file not found: {path}")

        suffix = path.suffix.lower()
        raw_text = path.read_text(encoding="utf-8")

        if suffix == ".json":
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                raise MalformedRecordError(f"Invalid JSON in {path}: {exc}") from exc
            if not isinstance(data, list):
                raise MalformedRecordError(f"Expected a JSON array in {path}")
            return data

        if suffix == ".jsonl":
            records = []
            for lineno, line in enumerate(raw_text.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise MalformedRecordError(
                        f"Invalid JSON on line {lineno} of {path}: {exc}"
                    ) from exc
                records.append(obj)
            return records

        raise LoaderError(
            f"Unsupported file extension {suffix!r} for {path}. "
            "Expected .json or .jsonl"
        )
