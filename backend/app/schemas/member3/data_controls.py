"""Member 3 user-data export and deletion responses."""

from datetime import datetime
from pydantic import BaseModel


class Member3DataExport(BaseModel):
    user_id: str
    exported_at: datetime
    insights: list[dict]
    alerts: list[dict]
    notifications: list[dict]
    emergency_workflows: list[dict]
    conversations: list[dict]
    guardian_decisions: list[dict]


class Member3PurgeResponse(BaseModel):
    user_id: str
    deleted_counts: dict[str, int]
    total_deleted: int
    purged_at: datetime
