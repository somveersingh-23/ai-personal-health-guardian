"""Deterministic safety orchestration for structured health evidence.

The engine deliberately does not diagnose conditions. It converts upstream
model output into a conservative next action before an LLM explains it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Iterable


SAFETY_POLICY_VERSION = "member3-safety-rules-v1"


class SafetyAction(str, Enum):
    NORMAL = "normal"
    OBSERVE = "observe"
    RE_MEASURE = "re_measure"
    SELF_CARE = "self_care"
    CAREGIVER_ALERT = "caregiver_alert"
    EMERGENCY_ESCALATION = "emergency_escalation"


@dataclass(frozen=True)
class SafetyInput:
    """Validated output expected from upstream baseline/fusion modules."""

    deviation_score: float
    confidence: float
    signal_quality: float
    evidence: tuple[str, ...] = ()
    critical_flags: tuple[str, ...] = ()
    user_confirmed_severe_symptoms: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("deviation_score", self.deviation_score),
            ("confidence", self.confidence),
            ("signal_quality", self.signal_quality),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a finite number")
            if not isfinite(value):
                raise ValueError(f"{name} must be a finite number")

        if self.deviation_score < 0:
            raise ValueError("deviation_score must be non-negative")
        for name, value in (
            ("confidence", self.confidence),
            ("signal_quality", self.signal_quality),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")

    @classmethod
    def from_evidence(
        cls,
        *,
        deviation_score: float,
        confidence: float,
        signal_quality: float,
        evidence: Iterable[str] = (),
        critical_flags: Iterable[str] = (),
        user_confirmed_severe_symptoms: bool = False,
    ) -> "SafetyInput":
        return cls(
            deviation_score=deviation_score,
            confidence=confidence,
            signal_quality=signal_quality,
            evidence=tuple(evidence),
            critical_flags=tuple(critical_flags),
            user_confirmed_severe_symptoms=user_confirmed_severe_symptoms,
        )


@dataclass(frozen=True)
class SafetyDecision:
    action: SafetyAction
    reason: str
    evidence: tuple[str, ...]
    requires_human_confirmation: bool
    policy_version: str = SAFETY_POLICY_VERSION
    disclaimer: str = (
        "This is a safety-oriented health insight, not a medical diagnosis."
    )


class SafetyEngine:
    """Apply explicit, testable rules in descending safety priority."""

    MIN_USABLE_QUALITY = 0.60
    MIN_USABLE_CONFIDENCE = 0.55
    HIGH_CONFIDENCE = 0.85
    MODERATE_DEVIATION = 1.50
    HIGH_DEVIATION = 2.50

    def evaluate(self, data: SafetyInput) -> SafetyDecision:
        evidence = tuple(item.strip() for item in data.evidence if item.strip())
        flags = tuple(item.strip() for item in data.critical_flags if item.strip())

        if data.user_confirmed_severe_symptoms:
            return SafetyDecision(
                action=SafetyAction.EMERGENCY_ESCALATION,
                reason="The user confirmed severe symptoms; urgent human help is required.",
                evidence=evidence + flags,
                requires_human_confirmation=True,
            )

        if (
            flags
            and data.confidence >= self.HIGH_CONFIDENCE
            and data.signal_quality >= self.MIN_USABLE_QUALITY
        ):
            return SafetyDecision(
                action=SafetyAction.EMERGENCY_ESCALATION,
                reason="A critical upstream flag is supported by high-confidence, usable evidence.",
                evidence=evidence + flags,
                requires_human_confirmation=True,
            )

        if data.signal_quality < self.MIN_USABLE_QUALITY or data.confidence < self.MIN_USABLE_CONFIDENCE:
            return SafetyDecision(
                action=SafetyAction.RE_MEASURE,
                reason="The available evidence is not reliable enough for a stronger action.",
                evidence=evidence + flags,
                requires_human_confirmation=False,
            )

        if flags or data.deviation_score >= self.HIGH_DEVIATION:
            return SafetyDecision(
                action=SafetyAction.CAREGIVER_ALERT,
                reason="A high deviation or critical flag needs timely human review.",
                evidence=evidence + flags,
                requires_human_confirmation=True,
            )

        if data.deviation_score >= self.MODERATE_DEVIATION:
            return SafetyDecision(
                action=SafetyAction.SELF_CARE,
                reason="A meaningful deviation is present with usable supporting evidence.",
                evidence=evidence,
                requires_human_confirmation=False,
            )

        if data.deviation_score > 0:
            return SafetyDecision(
                action=SafetyAction.OBSERVE,
                reason="The change is small and should be monitored without alarming the user.",
                evidence=evidence,
                requires_human_confirmation=False,
            )

        return SafetyDecision(
            action=SafetyAction.NORMAL,
            reason="No meaningful deviation was reported by the upstream models.",
            evidence=evidence,
            requires_human_confirmation=False,
        )
