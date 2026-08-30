"""Safety-controlled alert evaluation and lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Callable

from app.schemas.member3.alerts import (
    AlertEvaluationRequest,
    AlertEvaluationResponse,
    AlertListResponse,
    AlertPriority,
    AlertRecord,
    AlertStatus,
    new_alert_id,
)
from ml.safety import SafetyAction


class AlertNotFoundError(LookupError):
    pass


class InvalidAlertTransitionError(ValueError):
    pass


@dataclass(frozen=True)
class _StoredAlert:
    record: AlertRecord
    fingerprint: str


class InMemoryAlertRepository:
    """Thread-safe development repository; replace with persistence later."""

    def __init__(self) -> None:
        self._alerts: dict[str, _StoredAlert] = {}
        self._event_index: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def save(self, alert: _StoredAlert) -> None:
        with self._lock:
            self._alerts[alert.record.alert_id] = alert
            self._event_index[
                (alert.record.user_id, alert.record.event_id)
            ] = alert.record.alert_id

    def get(self, alert_id: str) -> _StoredAlert | None:
        with self._lock:
            return self._alerts.get(alert_id)

    def get_by_event(self, user_id: str, event_id: str) -> _StoredAlert | None:
        with self._lock:
            alert_id = self._event_index.get((user_id, event_id))
            return self._alerts.get(alert_id) if alert_id else None

    def list_for_user(self, user_id: str) -> list[_StoredAlert]:
        with self._lock:
            results = [item for item in self._alerts.values() if item.record.user_id == user_id]
        return sorted(results, key=lambda item: (item.record.created_at, item.record.alert_id), reverse=True)

    def delete_for_user(self, user_id: str) -> int:
        with self._lock:
            ids = [key for key, item in self._alerts.items() if item.record.user_id == user_id]
            for key in ids:
                item = self._alerts.pop(key)
                self._event_index.pop((item.record.user_id, item.record.event_id), None)
            return len(ids)


_PRIORITIES = {
    SafetyAction.SELF_CARE: AlertPriority.LOW,
    SafetyAction.RE_MEASURE: AlertPriority.MEDIUM,
    SafetyAction.CAREGIVER_ALERT: AlertPriority.HIGH,
    SafetyAction.EMERGENCY_ESCALATION: AlertPriority.CRITICAL,
}

_COPY = {
    SafetyAction.SELF_CARE: ("Health pattern changed", "Review the available insight and take the suggested self-care steps."),
    SafetyAction.RE_MEASURE: ("New measurement needed", "The available reading is not reliable enough. Please re-measure."),
    SafetyAction.CAREGIVER_ALERT: ("Human review recommended", "Please contact a caregiver or qualified healthcare professional promptly."),
    SafetyAction.EMERGENCY_ESCALATION: ("Urgent help recommended", "Contact local emergency services now or ask someone nearby to help."),
}

_ALLOWED_TRANSITIONS = {
    AlertStatus.ACTIVE: {AlertStatus.ACKNOWLEDGED, AlertStatus.DISMISSED, AlertStatus.RESOLVED},
    AlertStatus.ACKNOWLEDGED: {AlertStatus.RESOLVED},
    AlertStatus.DISMISSED: set(),
    AlertStatus.RESOLVED: set(),
}


class AlertService:
    """Create meaningful alerts without allowing this layer to calculate risk."""

    def __init__(
        self,
        repository: InMemoryAlertRepository | None = None,
        clock: Callable[[], datetime] | None = None,
        duplicate_window: timedelta = timedelta(minutes=30),
    ) -> None:
        if duplicate_window.total_seconds() < 0:
            raise ValueError("duplicate_window must be non-negative")
        self._repository = repository or InMemoryAlertRepository()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._duplicate_window = duplicate_window

    def evaluate(self, request: AlertEvaluationRequest) -> AlertEvaluationResponse:
        existing_event = self._repository.get_by_event(
            request.user_id, request.event_id
        )
        if existing_event is not None:
            return AlertEvaluationResponse(
                created=False,
                suppressed_reason="event_already_processed",
            )

        if request.safety_action in {SafetyAction.NORMAL, SafetyAction.OBSERVE}:
            return AlertEvaluationResponse(
                created=False,
                suppressed_reason="action_does_not_require_alert",
            )

        now = self._utc(self._clock())
        fingerprint = self._fingerprint(request)
        for stored in self._repository.list_for_user(request.user_id):
            if (
                stored.fingerprint == fingerprint
                and stored.record.status in {AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED}
                and now - self._utc(stored.record.created_at) <= self._duplicate_window
            ):
                return AlertEvaluationResponse(
                    created=False,
                    suppressed_reason="duplicate_within_cooldown",
                )

        priority = _PRIORITIES[request.safety_action]
        title, message = _COPY[request.safety_action]
        record = AlertRecord(
            alert_id=new_alert_id(),
            user_id=request.user_id,
            event_id=request.event_id,
            safety_action=request.safety_action,
            priority=priority,
            status=AlertStatus.ACTIVE,
            title=title,
            message=message,
            evidence=list(request.evidence),
            requires_human_confirmation=request.safety_action
            in {SafetyAction.CAREGIVER_ALERT, SafetyAction.EMERGENCY_ESCALATION},
            created_at=now,
            updated_at=now,
        )
        self._repository.save(_StoredAlert(record=record, fingerprint=fingerprint))
        return AlertEvaluationResponse(created=True, alert=record)

    def list_alerts(self, user_id: str) -> AlertListResponse:
        cleaned_user_id = " ".join(user_id.split())
        if not cleaned_user_id:
            raise ValueError("user_id must not be blank")
        alerts = [item.record for item in self._repository.list_for_user(cleaned_user_id)]
        return AlertListResponse(user_id=cleaned_user_id, alerts=alerts, count=len(alerts))

    def update_status(self, alert_id: str, status: AlertStatus) -> AlertRecord:
        stored = self._repository.get(alert_id)
        if stored is None:
            raise AlertNotFoundError("Alert not found")
        current = stored.record
        if status == current.status:
            return current
        if (
            current.priority == AlertPriority.CRITICAL
            and status == AlertStatus.DISMISSED
        ):
            raise InvalidAlertTransitionError(
                "Critical alerts cannot be dismissed; acknowledge or resolve them"
            )
        if status not in _ALLOWED_TRANSITIONS[current.status]:
            raise InvalidAlertTransitionError(
                f"Cannot transition alert from {current.status.value} to {status.value}"
            )
        updated = current.model_copy(
            update={"status": status, "updated_at": self._utc(self._clock())}
        )
        self._repository.save(replace(stored, record=updated))
        return updated

    def purge_user(self, user_id: str) -> int:
        return self._repository.delete_for_user(" ".join(user_id.split()))

    @staticmethod
    def _fingerprint(request: AlertEvaluationRequest) -> str:
        evidence = "|".join(sorted(item.casefold() for item in request.evidence))
        return f"{request.user_id.casefold()}::{request.safety_action.value}::{evidence}"

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
