from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TimelineEvent(BaseModel):
    id: int
    user_id: int
    event_type: str
    event_time: datetime
    value: float | None = None
    unit: str | None = None
    source: str | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class HealthTimelineResponse(BaseModel):
    user_id: int
    count: int
    events: list[TimelineEvent]
    start_time: datetime | None = None
    end_time: datetime | None = None
