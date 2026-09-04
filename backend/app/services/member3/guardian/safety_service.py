"""Thin application boundary around the pure deterministic safety engine."""

from app.schemas.member3.safety import SafetyEvaluationRequest, SafetyEvaluationResponse
from ml.safety import SafetyEngine, SafetyInput


class SafetyEvaluationService:
    def __init__(self, engine: SafetyEngine | None = None) -> None:
        self._engine = engine or SafetyEngine()

    def evaluate(self, request: SafetyEvaluationRequest) -> SafetyEvaluationResponse:
        decision = self._engine.evaluate(
            SafetyInput.from_evidence(
                deviation_score=request.deviation_score,
                confidence=request.confidence,
                signal_quality=request.signal_quality,
                evidence=request.evidence,
                critical_flags=request.critical_flags,
                user_confirmed_severe_symptoms=request.user_confirmed_severe_symptoms,
            )
        )
        return SafetyEvaluationResponse(
            action=decision.action,
            reason=decision.reason,
            evidence=decision.evidence,
            requires_human_confirmation=decision.requires_human_confirmation,
            disclaimer=decision.disclaimer,
        )
