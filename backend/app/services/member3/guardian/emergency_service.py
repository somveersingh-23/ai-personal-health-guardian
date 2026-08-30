"""Auditable emergency-workflow orchestration without external side effects."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Callable

from app.schemas.member3.emergency import (
    EmergencyAuditEvent,
    EmergencyCommand,
    EmergencyCommandRequest,
    EmergencyListResponse,
    EmergencyStartRequest,
    EmergencyState,
    EmergencyWorkflowRecord,
    new_workflow_id,
)


URGENT_INSTRUCTION = (
    "If there may be immediate danger, call your local emergency services now "
    "or ask someone nearby to call. Do not wait for this prototype."
)


class EmergencyWorkflowNotFoundError(LookupError):
    pass


class InvalidEmergencyTransitionError(ValueError):
    pass


class MissingCaregiverContactError(ValueError):
    pass


class InMemoryEmergencyRepository:
    def __init__(self) -> None:
        self._records: dict[str, EmergencyWorkflowRecord] = {}
        self._alert_index: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def save(self, record: EmergencyWorkflowRecord) -> None:
        with self._lock:
            self._records[record.workflow_id] = record
            self._alert_index[(record.user_id, record.alert_id)] = record.workflow_id

    def get(self, workflow_id: str) -> EmergencyWorkflowRecord | None:
        with self._lock:
            return self._records.get(workflow_id)

    def get_by_alert(self, user_id: str, alert_id: str) -> EmergencyWorkflowRecord | None:
        with self._lock:
            workflow_id = self._alert_index.get((user_id, alert_id))
            return self._records.get(workflow_id) if workflow_id else None

    def list_for_user(self, user_id: str) -> list[EmergencyWorkflowRecord]:
        with self._lock:
            records = [item for item in self._records.values() if item.user_id == user_id]
        return sorted(records, key=lambda item: (item.created_at, item.workflow_id), reverse=True)

    def delete_for_user(self, user_id: str) -> int:
        with self._lock:
            ids = [key for key, item in self._records.items() if item.user_id == user_id]
            for key in ids:
                item = self._records.pop(key)
                self._alert_index.pop((item.user_id, item.alert_id), None)
            return len(ids)


_NEXT_STATE = {
    EmergencyCommand.CONFIRM: {
        EmergencyState.AWAITING_CONFIRMATION: EmergencyState.CONFIRMED,
    },
    EmergencyCommand.RECORD_CAREGIVER_NOTIFICATION: {
        EmergencyState.CONFIRMED: EmergencyState.CAREGIVER_NOTIFICATION_RECORDED,
    },
    EmergencyCommand.REQUEST_EMERGENCY_CONTACT: {
        EmergencyState.CONFIRMED: EmergencyState.EMERGENCY_CONTACT_REQUESTED,
        EmergencyState.CAREGIVER_NOTIFICATION_RECORDED: EmergencyState.EMERGENCY_CONTACT_REQUESTED,
    },
    EmergencyCommand.CANCEL: {
        EmergencyState.AWAITING_CONFIRMATION: EmergencyState.CANCELLED,
        EmergencyState.CONFIRMED: EmergencyState.CANCELLED,
        EmergencyState.CAREGIVER_NOTIFICATION_RECORDED: EmergencyState.CANCELLED,
    },
    EmergencyCommand.RESOLVE: {
        EmergencyState.CONFIRMED: EmergencyState.RESOLVED,
        EmergencyState.CAREGIVER_NOTIFICATION_RECORDED: EmergencyState.RESOLVED,
        EmergencyState.EMERGENCY_CONTACT_REQUESTED: EmergencyState.RESOLVED,
    },
}


class EmergencyWorkflowService:
    """Record workflow intent; never claim an external call or message occurred."""

    def __init__(
        self,
        repository: InMemoryEmergencyRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository or InMemoryEmergencyRepository()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def start(self, request: EmergencyStartRequest) -> EmergencyWorkflowRecord:
        existing = self._repository.get_by_alert(request.user_id, request.alert_id)
        if existing is not None:
            return existing
        now = self._utc(self._clock())
        audit = EmergencyAuditEvent(
            sequence=1,
            event="workflow_started",
            actor_id="system",
            note="Emergency escalation received from upstream safety engine",
            occurred_at=now,
        )
        record = EmergencyWorkflowRecord(
            workflow_id=new_workflow_id(),
            user_id=request.user_id,
            alert_id=request.alert_id,
            state=EmergencyState.AWAITING_CONFIRMATION,
            safety_action=request.safety_action,
            safety_reason=request.safety_reason,
            evidence=tuple(request.evidence),
            caregiver_contact_id=request.caregiver_contact_id,
            urgent_instruction=URGENT_INSTRUCTION,
            external_action_performed=False,
            audit_events=(audit,),
            created_at=now,
            updated_at=now,
        )
        self._repository.save(record)
        return record

    def command(
        self, workflow_id: str, request: EmergencyCommandRequest
    ) -> EmergencyWorkflowRecord:
        current = self.get(workflow_id)
        transitions = _NEXT_STATE[request.command]
        target = transitions.get(current.state)
        if target is None:
            raise InvalidEmergencyTransitionError(
                f"Cannot apply {request.command.value} while workflow is {current.state.value}"
            )
        if (
            request.command == EmergencyCommand.RECORD_CAREGIVER_NOTIFICATION
            and current.caregiver_contact_id is None
        ):
            raise MissingCaregiverContactError(
                "A caregiver_contact_id is required before recording caregiver notification"
            )
        now = self._utc(self._clock())
        event = EmergencyAuditEvent(
            sequence=len(current.audit_events) + 1,
            event=request.command.value,
            actor_id=request.actor_id,
            note=request.note,
            occurred_at=now,
        )
        updated = current.model_copy(
            update={
                "state": target,
                "audit_events": (*current.audit_events, event),
                "updated_at": now,
                # This prototype records intent only; no connector is called.
                "external_action_performed": False,
            }
        )
        self._repository.save(updated)
        return updated

    def get(self, workflow_id: str) -> EmergencyWorkflowRecord:
        cleaned = " ".join(workflow_id.split())
        record = self._repository.get(cleaned)
        if record is None:
            raise EmergencyWorkflowNotFoundError("Emergency workflow not found")
        return record

    def list_workflows(self, user_id: str) -> EmergencyListResponse:
        cleaned = " ".join(user_id.split())
        if not cleaned:
            raise ValueError("user_id must not be blank")
        records = self._repository.list_for_user(cleaned)
        return EmergencyListResponse(user_id=cleaned, workflows=records, count=len(records))

    def purge_user(self, user_id: str) -> int:
        return self._repository.delete_for_user(" ".join(user_id.split()))

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
