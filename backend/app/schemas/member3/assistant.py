"""Pydantic request and response schemas for the Member 3 AI Guardian assistant.

All numeric confidence and signal-quality values are validated as finite
numbers strictly in the closed interval [0, 1].  Non-finite values (NaN,
±Infinity) and out-of-range values are rejected at the schema boundary
before reaching any service or provider.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Custom types
# ---------------------------------------------------------------------------

def _finite_fraction(label: str):
    """Return a Pydantic field validator factory for a [0, 1] finite float."""

    def _validate(value: float) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{label} must be a finite number between 0 and 1")
        if not isinstance(value, (int, float)):
            raise ValueError(f"{label} must be a finite number between 0 and 1")
        if not math.isfinite(value):
            raise ValueError(f"{label} must be a finite number between 0 and 1")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{label} must be between 0 and 1")
        return float(value)

    return _validate


# ---------------------------------------------------------------------------
# Evidence item
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    """A single structured health measurement supplied by the caller.

    All numeric fields except ``current_value`` and ``baseline_value``
    must be finite numbers in [0, 1].  ``current_value`` and
    ``baseline_value`` may be any finite float.
    """

    metric: Annotated[str, Field(min_length=1, description="Name of the health metric")]
    current_value: float = Field(description="Most recent observed value")
    baseline_value: float = Field(description="User's normal / baseline value")
    unit: Annotated[str, Field(min_length=1, description="Unit of measurement, e.g. 'bpm'")]
    direction: Annotated[str, Field(min_length=1, description="Trend, e.g. 'elevated', 'decreased'")]
    confidence: float = Field(description="Model confidence in [0, 1]")
    signal_quality: float = Field(description="Sensor signal quality in [0, 1]")
    timestamp: Optional[datetime] = Field(default=None, description="When the measurement was taken")

    @field_validator("current_value", "baseline_value", mode="before")
    @classmethod
    def _validate_finite_float(cls, value: float) -> float:
        if isinstance(value, bool):
            raise ValueError("value must be a finite number")
        if not isinstance(value, (int, float)):
            raise ValueError("value must be a finite number")
        if not math.isfinite(float(value)):
            raise ValueError("value must be a finite number")
        return float(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        return _finite_fraction("confidence")(value)

    @field_validator("signal_quality", mode="before")
    @classmethod
    def _validate_signal_quality(cls, value: float) -> float:
        return _finite_fraction("signal_quality")(value)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class ExplainRequest(BaseModel):
    """Request body for ``POST /api/v1/member3/assistant/explain``.

    ``conversation_id`` is auto-generated (UUID4) when omitted so the
    caller can track multi-turn conversations without managing IDs itself.
    """

    user_id: Annotated[str, Field(min_length=1, description="Opaque user identifier")]
    question: Annotated[
        str,
        Field(min_length=1, description="The user's health question (untrusted content)"),
    ]
    evidence: Annotated[
        list[EvidenceItem],
        Field(min_length=1, description="Structured health measurements from upstream models"),
    ]
    safety_action: Annotated[
        str,
        Field(min_length=1, description="SafetyAction value from the safety engine"),
    ]
    safety_reason: Annotated[
        str,
        Field(min_length=1, description="Human-readable reason for the safety action"),
    ]
    conversation_id: Optional[str] = Field(
        default=None,
        description="Existing conversation ID; auto-generated when omitted",
    )
    locale: str = Field(
        default="en",
        description="BCP-47 locale tag; falls back to 'en' if unsupported",
    )

    @model_validator(mode="after")
    def _generate_conversation_id(self) -> "ExplainRequest":
        if not self.conversation_id:
            object.__setattr__(self, "conversation_id", str(uuid.uuid4()))
        return self

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class ExplainResponse(BaseModel):
    """Response body for ``POST /api/v1/member3/assistant/explain``.

    The ``safety_action`` field echoes the **incoming** action verbatim.
    It is never modified by the assistant or the explanation service.
    """

    conversation_id: str = Field(description="Conversation tracking identifier")
    answer: str = Field(description="The generated health explanation")
    safety_action: str = Field(
        description="The safety action echoed unchanged from the request"
    )
    evidence_used: list[str] = Field(
        description="Metric names from the supplied evidence that were referenced"
    )
    limitations: list[str] = Field(
        description="Limitations or caveats about the evidence quality"
    )
    disclaimer: str = Field(description="Medical disclaimer statement")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp when the response was generated",
    )
