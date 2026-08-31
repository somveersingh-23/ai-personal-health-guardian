"""RAG context builder for the Member 3 AI Guardian assistant integration.

Converts retrieval results into an immutable, structured context block
suitable for the existing AI explanation service/provider.

Safety invariants:
- Never changes safety_action or safety_reason.
- Never combines retrieved text with system instructions.
- Treats all retrieved passages as UNTRUSTED REFERENCE CONTENT.
- Removes control characters.
- Produces deterministic output for identical inputs.
- Handles no-results safely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.schemas.member3.rag import RetrievalResult


# ---------------------------------------------------------------------------
# Immutable context block
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RagContextBlock:
    """Immutable, structured context block produced by the adapter.

    ``safety_action`` and ``safety_reason`` are echoed verbatim from the
    upstream safety decision — this adapter never modifies them.

    ``passages`` is a tuple of (title, sanitized_text, source_name) tuples.
    ``has_results`` is False when no relevant chunks were found.
    """

    safety_action: str
    safety_reason: str
    passages: tuple[tuple[str, str, str], ...]  # (title, text, source_name)
    citations: tuple[str, ...]
    has_results: bool
    limitations: tuple[str, ...]


# ---------------------------------------------------------------------------
# Control character removal
# ---------------------------------------------------------------------------

_CTRL_CHAR_PATTERN = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _strip_control_chars(text: str) -> str:
    return _CTRL_CHAR_PATTERN.sub("", text).strip()


# ---------------------------------------------------------------------------
# Injection patterns — secondary structural check (not sole security boundary)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?|constraints?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"change\s+(the\s+)?safety\s+action", re.IGNORECASE),
    re.compile(r"diagnose\s+(the\s+)?user", re.IGNORECASE),
    re.compile(r"reveal\s+(secrets?|api\s*key|password)", re.IGNORECASE),
    re.compile(r"execute\s+(command|code|script)", re.IGNORECASE),
    re.compile(r"override\s+(safety|constraint|rule)", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
]


def _sanitize_passage(text: str) -> str:
    """Strip control characters and neutralize injection patterns."""
    text = _strip_control_chars(text)
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[content removed]", text)
    return text


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

_MAX_PASSAGE_CHARS = 800
_MAX_TOTAL_CHARS = 3000


class RagContextBuilder:
    """Convert retrieval results into an immutable RagContextBlock.

    The builder is stateless; construct a new instance per request or
    share a single instance freely.
    """

    def build(
        self,
        *,
        safety_action: str,
        safety_reason: str,
        results: list[RetrievalResult],
        limitations: Optional[list[str]] = None,
    ) -> RagContextBlock:
        """Build an immutable context block from retrieval results.

        Parameters
        ----------
        safety_action:
            Echoed verbatim from the upstream safety decision.
        safety_reason:
            Echoed verbatim from the upstream safety decision.
        results:
            Retrieval results from the retrieval service.
        limitations:
            Optional limitation strings from the retrieval service.
        """
        passages: list[tuple[str, str, str]] = []
        citations: list[str] = []
        total_chars = 0

        for result in results:
            # Sanitize passage (secondary structural check)
            sanitized = _sanitize_passage(result.passage)
            sanitized = sanitized[:_MAX_PASSAGE_CHARS]

            if total_chars + len(sanitized) > _MAX_TOTAL_CHARS:
                break
            total_chars += len(sanitized)

            clean_title = _strip_control_chars(result.title)
            clean_source_name = _strip_control_chars(result.source_name)
            passages.append((
                clean_title,
                sanitized,
                clean_source_name,
            ))

            # Citation: title + source_name (never raw URLs in citations)
            citations.append(
                f"{clean_title} — {clean_source_name}"
            )

        return RagContextBlock(
            # Echo safety fields unchanged — NEVER modify them
            safety_action=safety_action,
            safety_reason=safety_reason,
            passages=tuple(passages),
            citations=tuple(citations),
            has_results=len(passages) > 0,
            limitations=tuple(limitations or []),
        )
