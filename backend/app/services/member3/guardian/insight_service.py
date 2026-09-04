"""Build evidence-grounded insights without calculating or changing risk."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Callable

from app.schemas.member3.insights import (
    InsightCreateRequest,
    InsightListResponse,
    InsightRecord,
    InsightSeverity,
    InsightStatus,
    new_insight_id,
)
from ml.safety import SafetyAction


DISCLAIMER = (
    "This insight describes supplied health evidence and is not a medical "
    "diagnosis or professional medical advice."
)


class InsightNotFoundError(LookupError):
    pass


class InvalidInsightTransitionError(ValueError):
    pass


class InMemoryInsightRepository:
    def __init__(self) -> None:
        self._records: dict[str, InsightRecord] = {}
        self._source_index: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def save(self, record: InsightRecord) -> None:
        with self._lock:
            self._records[record.insight_id] = record
            self._source_index[(record.user_id, record.source_event_id)] = record.insight_id

    def get(self, insight_id: str) -> InsightRecord | None:
        with self._lock:
            return self._records.get(insight_id)

    def get_by_source(self, user_id: str, source_event_id: str) -> InsightRecord | None:
        with self._lock:
            insight_id = self._source_index.get((user_id, source_event_id))
            return self._records.get(insight_id) if insight_id else None

    def list_for_user(self, user_id: str) -> list[InsightRecord]:
        with self._lock:
            records = [record for record in self._records.values() if record.user_id == user_id]
        return sorted(records, key=lambda record: (record.created_at, record.insight_id), reverse=True)

    def delete_for_user(self, user_id: str) -> int:
        with self._lock:
            ids = [key for key, record in self._records.items() if record.user_id == user_id]
            for key in ids:
                record = self._records.pop(key)
                self._source_index.pop((record.user_id, record.source_event_id), None)
            return len(ids)


_SEVERITY = {
    SafetyAction.NORMAL: InsightSeverity.INFORMATIONAL,
    SafetyAction.OBSERVE: InsightSeverity.LOW,
    SafetyAction.RE_MEASURE: InsightSeverity.MODERATE,
    SafetyAction.SELF_CARE: InsightSeverity.MODERATE,
    SafetyAction.CAREGIVER_ALERT: InsightSeverity.HIGH,
    SafetyAction.EMERGENCY_ESCALATION: InsightSeverity.CRITICAL,
}

_TITLE = {
    SafetyAction.NORMAL: "Your readings are within the reported pattern",
    SafetyAction.OBSERVE: "A small change was detected",
    SafetyAction.RE_MEASURE: "A clearer measurement is needed",
    SafetyAction.SELF_CARE: "Your recovery pattern has changed",
    SafetyAction.CAREGIVER_ALERT: "Timely human review is recommended",
    SafetyAction.EMERGENCY_ESCALATION: "Urgent professional help is recommended",
}

_ALLOWED_TRANSITIONS = {
    InsightStatus.NEW: {InsightStatus.VIEWED, InsightStatus.ARCHIVED},
    InsightStatus.VIEWED: {InsightStatus.ARCHIVED},
    InsightStatus.ARCHIVED: set(),
}


class InsightService:
    def __init__(
        self,
        repository: InMemoryInsightRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository or InMemoryInsightRepository()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create(self, request: InsightCreateRequest) -> InsightRecord:
        existing = self._repository.get_by_source(request.user_id, request.source_event_id)
        if existing is not None:
            return existing
        now = self._utc(self._clock())
        limitations = self._limitations(request)
        record = InsightRecord(
            insight_id=new_insight_id(),
            user_id=request.user_id,
            source_event_id=request.source_event_id,
            insight_type=request.insight_type,
            safety_action=request.safety_action,
            severity=_SEVERITY[request.safety_action],
            status=InsightStatus.NEW,
            title=_TITLE[request.safety_action],
            summary=self._summary(request),
            evidence=tuple(request.evidence),
            limitations=limitations,
            disclaimer=DISCLAIMER,
            created_at=now,
            updated_at=now,
        )
        self._repository.save(record)
        return record

    def get(self, insight_id: str) -> InsightRecord:
        record = self._repository.get(" ".join(insight_id.split()))
        if record is None:
            raise InsightNotFoundError("Insight not found")
        return record

    def get_for_user(self, insight_id: str, user_id: str) -> InsightRecord:
        record = self.get(insight_id)
        if record.user_id != " ".join(user_id.split()):
            # Do not reveal another user's record identifier.
            raise InsightNotFoundError("Insight not found")
        return record

    def list_insights(self, user_id: str) -> InsightListResponse:
        cleaned = " ".join(user_id.split())
        if not cleaned:
            raise ValueError("user_id must not be blank")
        records = self._repository.list_for_user(cleaned)
        return InsightListResponse(user_id=cleaned, insights=records, count=len(records))

    def update_status(self, insight_id: str, status: InsightStatus) -> InsightRecord:
        current = self.get(insight_id)
        return self._update_status(current, status)

    def update_status_for_user(
        self, insight_id: str, user_id: str, status: InsightStatus
    ) -> InsightRecord:
        return self._update_status(self.get_for_user(insight_id, user_id), status)

    def _update_status(self, current: InsightRecord, status: InsightStatus) -> InsightRecord:
        if status == current.status:
            return current
        if status not in _ALLOWED_TRANSITIONS[current.status]:
            raise InvalidInsightTransitionError(
                f"Cannot transition insight from {current.status.value} to {status.value}"
            )
        updated = current.model_copy(
            update={"status": status, "updated_at": self._utc(self._clock())}
        )
        self._repository.save(updated)
        return updated

    def purge_user(self, user_id: str) -> int:
        return self._repository.delete_for_user(" ".join(user_id.split()))

    @staticmethod
    def _summary(request: InsightCreateRequest) -> str:
        descriptions = [
            f"{item.metric}: {item.direction} "
            f"({item.current_value:g} {item.unit}; baseline {item.baseline_value:g} {item.unit})"
            for item in request.evidence
        ]
        return f"{request.safety_reason}. Evidence: " + "; ".join(descriptions) + "."

    @staticmethod
    def _limitations(request: InsightCreateRequest) -> tuple[str, ...]:
        notes: list[str] = []
        if any(item.confidence < 0.7 for item in request.evidence):
            notes.append("Some supplied model confidence values are limited.")
        if any(item.signal_quality < 0.7 for item in request.evidence):
            notes.append("Some supplied sensor readings have limited signal quality.")
        return tuple(notes)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
