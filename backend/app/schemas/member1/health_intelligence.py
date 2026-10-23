from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthInsight(BaseModel):
    insight_id: str
    generated_at: datetime | str
    insight_type: str
    category: str
    severity: str
    priority: int = 0
    confidence: float = 0.0
    title: str
    message: str
    recommended_action: str
    supporting_data: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class HealthIntelligenceResponse(BaseModel):
    user_id: int
    generated_at: datetime | str
    digital_twin_state: str = "no_data"
    anomaly_score: float = 0.0
    insight_count: int = 0
    insights: list[HealthInsight] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class DigitalTwinResponse(BaseModel):
    user_id: int
    generated_at: datetime | str
    latest_event_time: datetime | str | None = None
    state: str = "no_data"
    anomaly_score: float = 0.0
    summary: dict[str, Any] = Field(default_factory=dict)
    current_metrics: list[dict[str, Any]] = Field(default_factory=list)
    vitals: dict[str, Any] = Field(default_factory=dict)
    lifestyle: dict[str, Any] = Field(default_factory=dict)
    baselines: list[dict[str, Any]] = Field(default_factory=list)
    trends: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")
