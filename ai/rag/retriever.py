"""Deterministic local keyword retriever for the Member 3 RAG pipeline.

This is a keyword/token-based retriever that does not require:
- an API key
- an external vector database
- internet access
- model downloads
- external LLM calls

Scoring weights (higher = more important):
- title match:   3.0 per matching token
- topic match:   2.5 per matching token
- keyword match: 2.0 per matching token
- content match: 1.0 per matching token
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional, Sequence

from .models import KnowledgeChunk


# ---------------------------------------------------------------------------
# Stop words
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "it", "its", "this", "that", "these",
    "those", "my", "your", "his", "her", "our", "their", "i", "me", "you",
    "he", "she", "we", "they", "what", "why", "how", "when", "where",
    "which", "who", "whom", "not", "no", "so", "if", "as",
})

# Scoring weights
_W_TITLE = 3.0
_W_TOPIC = 2.5
_W_KEYWORD = 2.0
_W_CONTENT = 1.0

# Default minimum relevance threshold
_DEFAULT_THRESHOLD = 0.5
_DEFAULT_TOP_K = 3
_MAX_TOP_K = 10
_MIN_TOP_K = 1


@dataclass(frozen=True)
class RetrievalRecord:
    """A single retrieval result with score and source metadata."""

    chunk: KnowledgeChunk
    score: float
    sanitized_content: str  # prompt-injection-sanitized version of content
    injection_flagged: bool = False


# ---------------------------------------------------------------------------
# Injection detection patterns (structural check — not sole security boundary)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?|constraints?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"act\s+as\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"change\s+(the\s+)?safety\s+action", re.IGNORECASE),
    re.compile(r"diagnose\s+(the\s+)?user", re.IGNORECASE),
    re.compile(r"reveal\s+(secrets?|api\s*key|password)", re.IGNORECASE),
    re.compile(r"execute\s+(command|code|script)", re.IGNORECASE),
    re.compile(r"override\s+(safety|constraint|rule)", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)", re.IGNORECASE),
]


def _sanitize_content(text: str) -> tuple[str, bool]:
    """Remove injection patterns and control characters; flag if any removed."""
    # Remove control characters (except newline and tab)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    flagged = False
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[content removed]", cleaned)
            flagged = True
    return cleaned, flagged


def _tokenize(text: str) -> list[str]:
    """Lowercase, remove punctuation, split, and filter stop words."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _score_chunk(query_tokens: set[str], chunk: KnowledgeChunk) -> float:
    """Return a relevance score for a single chunk."""
    if not query_tokens:
        return 0.0

    score = 0.0
    n_terms = len(query_tokens)

    title_tokens = set(_tokenize(chunk.title))
    topic_tokens = set(_tokenize(chunk.topic.replace("_", " ")))
    keyword_tokens = set(chunk.keywords)  # already lowercased
    content_tokens = set(_tokenize(chunk.content))

    for token in query_tokens:
        if token in title_tokens:
            score += _W_TITLE
        if token in topic_tokens:
            score += _W_TOPIC
        if token in keyword_tokens:
            score += _W_KEYWORD
        if token in content_tokens:
            score += _W_CONTENT

    # Normalise by number of query terms
    return score / n_terms


class LocalKeywordRetriever:
    """Deterministic, offline keyword-based retriever.

    Does not use vector search, embeddings, or external services.
    Identical inputs always produce identical outputs.
    """

    def __init__(
        self,
        chunks: Sequence[KnowledgeChunk],
        threshold: float = _DEFAULT_THRESHOLD,
    ) -> None:
        if not math.isfinite(threshold) or threshold < 0:
            raise ValueError("threshold must be a finite non-negative number")
        # Store a defensive copy; never mutate the originals
        self._chunks: tuple[KnowledgeChunk, ...] = tuple(chunks)
        self._threshold = threshold

    def retrieve(
        self,
        query: str,
        top_k: int = _DEFAULT_TOP_K,
        topic_filter: Optional[str | Sequence[str]] = None,
    ) -> list[RetrievalRecord]:
        """Return the top-k most relevant approved chunks for the query.

        Parameters
        ----------
        query:
            The sanitized user question. Must be non-empty.
        top_k:
            Maximum number of results (1–10).
        topic_filter:
            If supplied, restrict results to chunks with this exact topic.

        Returns
        -------
        list[RetrievalRecord]
            Scored, deduplicated, ordered results.  Empty if nothing is
            above the relevance threshold.
        """
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        if not isinstance(top_k, int) or isinstance(top_k, bool):
            raise ValueError("top_k must be an integer")
        if top_k < _MIN_TOP_K or top_k > _MAX_TOP_K:
            raise ValueError(
                f"top_k must be between {_MIN_TOP_K} and {_MAX_TOP_K}, got {top_k}"
            )

        query_tokens = set(_tokenize(query))

        candidates = self._chunks
        if topic_filter is not None:
            raw_topics = [topic_filter] if isinstance(topic_filter, str) else list(topic_filter)
            topics = {
                topic.strip().lower()
                for topic in raw_topics
                if isinstance(topic, str) and topic.strip()
            }
            if not topics:
                return []
            candidates = tuple(
                c for c in candidates
                if c.topic.lower() in topics
            )

        scored: list[tuple[float, str, str, KnowledgeChunk]] = []
        for chunk in candidates:
            score = _score_chunk(query_tokens, chunk)
            if score >= self._threshold:
                # Stable tie-breaking: (score DESC, document_id ASC, chunk_id ASC)
                scored.append((-score, chunk.document_id, chunk.chunk_id, chunk))

        scored.sort(key=lambda x: (x[0], x[1], x[2]))

        results: list[RetrievalRecord] = []
        seen_chunk_ids: set[str] = set()
        for neg_score, _, _, chunk in scored[:top_k * 2]:  # overfetch then dedup
            if chunk.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk.chunk_id)
            sanitized, flagged = _sanitize_content(chunk.content)
            results.append(RetrievalRecord(
                chunk=chunk,
                score=-neg_score,
                sanitized_content=sanitized,
                injection_flagged=flagged,
            ))
            if len(results) >= top_k:
                break

        return results
