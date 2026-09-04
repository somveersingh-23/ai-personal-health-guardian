"""Explanation service for the Member 3 AI Guardian assistant.

This service is the single orchestration point between the API layer,
the upstream safety decision, and the assistant provider.  It enforces
all safety constraints that are not already enforced by the schema or
the provider protocol.

Safety invariants upheld here:
- The ``safety_action`` from the request is **always** echoed unchanged
  into the response.
- Only evidence supplied in the request is referenced; the service never
  creates or injects additional evidence.
- The service never calls a real LLM unless an external provider is
  explicitly injected (dependency injection via constructor).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ai.assistant.provider import AssistantProvider, EvidenceSummary, StructuredPromptContext
from ai.assistant.template_provider import TemplateProvider
from ai.prompts.sanitize import sanitize_user_question
from app.schemas.member3.assistant import EvidenceItem, ExplainRequest, ExplainResponse
from ml.safety import SafetyAction

# ---------------------------------------------------------------------------
# Service-specific exceptions
# ---------------------------------------------------------------------------

_MEDICAL_DISCLAIMER = (
    "Important: This is a safety-oriented health insight, not a medical "
    "diagnosis or professional medical advice. Always consult a qualified "
    "healthcare professional before making any health decisions."
)

_SUPPORTED_ACTIONS = {action.value for action in SafetyAction}

# Confidence / quality threshold below which we note limited reliability.
_LOW_CONFIDENCE_THRESHOLD = 0.70
_LOW_QUALITY_THRESHOLD = 0.70


class UnsupportedActionError(ValueError):
    """Raised when the request carries an unrecognised ``safety_action``."""


class InsufficientEvidenceError(ValueError):
    """Raised when no usable evidence items remain after normalisation."""


class ProviderError(RuntimeError):
    """Raised when the assistant provider raises an unexpected error."""


# ---------------------------------------------------------------------------
# Explanation service
# ---------------------------------------------------------------------------

class ExplanationService:
    """Orchestrate evidence normalisation, prompt construction, and generation.

    Parameters
    ----------
    provider:
        An ``AssistantProvider`` implementation.  Defaults to
        ``TemplateProvider`` so the service works offline without any
        external API key.
    """

    def __init__(self, provider: Optional[AssistantProvider] = None) -> None:
        self._provider: AssistantProvider = provider if provider is not None else TemplateProvider()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def explain(self, request: ExplainRequest) -> ExplainResponse:
        """Generate a safe health explanation from structured evidence.

        Parameters
        ----------
        request:
            A validated ``ExplainRequest`` instance.

        Returns
        -------
        ExplainResponse
            The generated explanation with the **same** ``safety_action``
            as the request, evidence metadata, limitations, and disclaimer.

        Raises
        ------
        UnsupportedActionError
            If ``request.safety_action`` is not a known ``SafetyAction``.
        InsufficientEvidenceError
            If no usable evidence items remain after normalisation.
        ProviderError
            If the provider raises an unexpected error.
        """
        self._validate_action(request.safety_action)

        normalised_evidence = self._normalise_evidence(request.evidence)
        if not normalised_evidence:
            raise InsufficientEvidenceError(
                "No usable evidence items after normalisation. "
                "Each item must have a non-blank metric name."
            )

        limitations = self._build_limitations(normalised_evidence, request.safety_action)

        context = self._build_context(
            request=request,
            normalised_evidence=normalised_evidence,
            limitations=limitations,
        )

        answer = self._call_provider(context)

        return ExplainResponse(
            conversation_id=request.conversation_id or "",  # always set by schema validator
            answer=answer,
            # Echo the incoming action verbatim — never modified.
            safety_action=request.safety_action,
            evidence_used=[item.metric for item in normalised_evidence],
            limitations=list(limitations),
            disclaimer=_MEDICAL_DISCLAIMER,
            generated_at=datetime.now(tz=timezone.utc),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_action(action: str) -> None:
        if action not in _SUPPORTED_ACTIONS:
            raise UnsupportedActionError(
                f"Unrecognised safety_action '{action}'. "
                f"Supported values: {sorted(_SUPPORTED_ACTIONS)}"
            )

    @staticmethod
    def _normalise_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Strip evidence items with blank metric names; preserve order."""
        return [item for item in items if item.metric.strip()]

    @staticmethod
    def _build_limitations(
        evidence: list[EvidenceItem],
        action: str,
    ) -> tuple[str, ...]:
        """Build human-readable limitation notes from evidence quality."""
        notes: list[str] = []
        low_confidence_metrics = [
            item.metric
            for item in evidence
            if item.confidence < _LOW_CONFIDENCE_THRESHOLD
        ]
        low_quality_metrics = [
            item.metric
            for item in evidence
            if item.signal_quality < _LOW_QUALITY_THRESHOLD
        ]
        if low_confidence_metrics:
            joined = ", ".join(low_confidence_metrics)
            notes.append(
                f"Limited model confidence for: {joined}. "
                "These observations may be less reliable."
            )
        if low_quality_metrics:
            joined = ", ".join(low_quality_metrics)
            notes.append(
                f"Limited sensor signal quality for: {joined}. "
                "A re-measurement may improve accuracy."
            )
        if action == SafetyAction.RE_MEASURE.value:
            notes.append(
                "The overall sensor quality was too low to draw a confident "
                "conclusion — a fresh reading is recommended."
            )
        return tuple(notes)

    @staticmethod
    def _build_context(
        *,
        request: ExplainRequest,
        normalised_evidence: list[EvidenceItem],
        limitations: tuple[str, ...],
    ) -> StructuredPromptContext:
        """Build the immutable provider context from the validated request."""
        evidence_summaries = tuple(
            EvidenceSummary(
                metric=item.metric,
                current_value=item.current_value,
                baseline_value=item.baseline_value,
                unit=item.unit,
                direction=item.direction,
                confidence=item.confidence,
                signal_quality=item.signal_quality,
            )
            for item in normalised_evidence
        )

        has_low_confidence = any(
            item.confidence < _LOW_CONFIDENCE_THRESHOLD for item in normalised_evidence
        )
        has_low_quality = any(
            item.signal_quality < _LOW_QUALITY_THRESHOLD for item in normalised_evidence
        )

        sanitised_question = sanitize_user_question(request.question)

        return StructuredPromptContext(
            safety_action=request.safety_action,
            safety_reason=request.safety_reason,
            evidence=evidence_summaries,
            user_question=sanitised_question,
            locale=request.locale or "en",
            has_low_confidence=has_low_confidence,
            has_low_quality=has_low_quality,
            limitations=limitations,
        )

    def _call_provider(self, context: StructuredPromptContext) -> str:
        """Delegate to the provider; wrap any exception as ``ProviderError``."""
        try:
            answer = self._provider.generate(context)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Assistant provider failed: {exc}") from exc

        if not answer or not answer.strip():
            raise ProviderError("Assistant provider returned an empty response.")

        return answer
