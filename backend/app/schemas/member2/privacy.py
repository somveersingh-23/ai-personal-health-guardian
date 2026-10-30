"""Privacy-control contracts for the Member 2 data domain."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.member2.health_event import HealthEventResponse


class Member2DataExportPage(BaseModel):
    user_id: int
    schema_version: Literal["1.0.0"] = "1.0.0"
    scope: Literal["active_normalized_observations"] = "active_normalized_observations"
    consistency: Literal["live_keyset"] = "live_keyset"
    exported_at: datetime
    events: list[HealthEventResponse]
    next_after_id: int | None
    has_more: bool


class Member2DataPurgeRequest(BaseModel):
    """Requires an explicit destructive-action phrase from the calling UI."""

    model_config = ConfigDict(extra="forbid")

    confirmation: Literal["DELETE_MEMBER2_DATA"]


class Member2DataPurgeResponse(BaseModel):
    user_id: int
    deleted_counts: dict[str, int]
    completed_at: datetime
    collection_paused: bool = True


class Member2CollectionResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: Literal["RESUME_MEMBER2_COLLECTION"]


__all__ = [
    "Member2DataExportPage",
    "Member2DataPurgeRequest",
    "Member2DataPurgeResponse",
]
