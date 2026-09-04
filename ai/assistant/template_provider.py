"""Deterministic template-based provider.

Works locally without any external API key or network connection.
Used as the default provider in tests and development.

A real LLM provider can be added later by creating a new class that
implements the ``AssistantProvider`` protocol (see ``provider.py``)
without changing any service or router code.
"""

from __future__ import annotations

from .provider import AssistantProvider, StructuredPromptContext  # noqa: F401 — satisfies Protocol

_DISCLAIMER = (
    "Important: This is a safety-oriented health insight, not a medical "
    "diagnosis or professional medical advice. Always consult a qualified "
    "healthcare professional before making any health decisions."
)

# Per-action opening sentence templates.
_ACTION_OPENINGS: dict[str, str] = {
    "normal": (
        "Based on the measurements provided, your health indicators appear "
        "to be within their normal range."
    ),
    "observe": (
        "A small change has been noticed in your health indicators. "
        "No immediate action is needed, but it is worth keeping an eye on "
        "how things develop over the next few days."
    ),
    "re_measure": (
        "The sensor readings collected at this time are not reliable enough "
        "to draw a confident conclusion. Please try taking another reading "
        "in a quiet environment to improve accuracy."
    ),
    "self_care": (
        "A meaningful change has been detected in your health indicators. "
        "Some gentle self-care steps may be helpful right now."
    ),
    "caregiver_alert": (
        "Your health indicators suggest a pattern that warrants timely "
        "attention from someone who knows your health well, such as a "
        "caregiver, family member, or doctor."
    ),
    "emergency_escalation": (
        "The information available indicates a situation that requires "
        "immediate professional attention. Please call emergency services "
        "(such as 112 or 999) or ask someone nearby to help you contact "
        "them right away."
    ),
}

_UNCERTAINTY_NOTE = (
    " Please note that some of the measurements used have limited "
    "confidence or signal quality, so these observations carry uncertainty."
)

_LIMITATION_INTRO = "Keep in mind the following limitations: "

_CLOSING: dict[str, str] = {
    "normal": "Continue with your usual routine and monitor as normal.",
    "observe": (
        "Monitor your readings over the next 24–48 hours. "
        "If the change persists or worsens, contact your healthcare provider."
    ),
    "re_measure": (
        "Once a better-quality reading is available, the system will reassess "
        "your situation."
    ),
    "self_care": (
        "Rest, stay hydrated, and avoid strenuous activity until your "
        "readings return to your normal range. If symptoms worsen, contact "
        "your healthcare provider."
    ),
    "caregiver_alert": (
        "Please inform your caregiver or healthcare provider of this reading "
        "as soon as possible."
    ),
    "emergency_escalation": (
        "Do not wait — contact emergency services now. "
        "If you are unable to call, ask someone near you to call on your behalf."
    ),
}


class TemplateProvider:
    """Deterministic, offline assistant provider.

    Generates structured, action-appropriate health explanations from
    fixed templates.  Identical inputs always produce identical outputs.
    """

    def generate(self, context: StructuredPromptContext) -> str:  # noqa: D401
        """Return a safe, template-based health explanation."""
        action = context.safety_action
        opening = _ACTION_OPENINGS.get(
            action,
            "Your health data has been assessed and a recommendation has been prepared.",
        )

        parts: list[str] = [opening]

        # Describe the supplied evidence (never invent new values).
        if context.evidence:
            parts.append("Here is what your data shows:")
            for item in context.evidence:
                direction_note = (
                    f"your {item.metric} is {item.direction} "
                    f"(current: {item.current_value} {item.unit}, "
                    f"baseline: {item.baseline_value} {item.unit})"
                )
                parts.append(f"  • {direction_note}.")

        # Mention uncertainty when confidence or quality is limited.
        if context.has_low_confidence or context.has_low_quality:
            parts.append(_UNCERTAINTY_NOTE)

        # Surface any structured limitations.
        if context.limitations:
            limitation_text = "; ".join(context.limitations)
            parts.append(f"{_LIMITATION_INTRO}{limitation_text}.")

        # Add an action-appropriate next step.
        closing = _CLOSING.get(action, "Please consult your healthcare provider.")
        parts.append(closing)

        # Always append the medical disclaimer.
        parts.append(_DISCLAIMER)

        return "\n\n".join(parts)
