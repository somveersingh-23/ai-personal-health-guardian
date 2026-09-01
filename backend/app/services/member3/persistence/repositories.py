"""Synchronous SQLAlchemy adapters for the existing Member 3 services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.member3.guardian_record import Member3GuardianRecord
from app.schemas.member3.alerts import AlertRecord
from app.schemas.member3.caregivers import CaregiverLink
from app.schemas.member3.conversations import ConversationRecord
from app.schemas.member3.emergency import EmergencyWorkflowRecord
from app.schemas.member3.guardian import GuardianProcessResponse
from app.schemas.member3.insights import InsightRecord
from app.schemas.member3.notifications import NotificationChannel, NotificationRecord
from app.services.member3.guardian.alert_service import _StoredAlert

ModelT = TypeVar("ModelT", bound=BaseModel)


class _JsonRepository:
    def __init__(self, sessions: sessionmaker[Session], record_type: str, model: type[ModelT]):
        self._sessions = sessions
        self._record_type = record_type
        self._model = model

    def _save(self, record_id: str, user_id: str, value: ModelT, secondary: str | None = None, metadata: str | None = None) -> None:
        with self._sessions.begin() as session:
            row = session.scalar(select(Member3GuardianRecord).where(
                Member3GuardianRecord.record_type == self._record_type,
                Member3GuardianRecord.record_id == record_id,
            ))
            if row is None:
                row = Member3GuardianRecord(record_type=self._record_type, record_id=record_id, user_id=user_id, payload="")
                session.add(row)
            row.user_id = user_id
            row.secondary_key = secondary
            row.metadata_value = metadata
            row.payload = value.model_dump_json()
            row.updated_at = datetime.now(timezone.utc)

    def _get(self, record_id: str) -> ModelT | None:
        with self._sessions() as session:
            row = session.scalar(select(Member3GuardianRecord).where(
                Member3GuardianRecord.record_type == self._record_type,
                Member3GuardianRecord.record_id == record_id,
            ))
            return self._model.model_validate_json(row.payload) if row else None

    def _get_row_by_secondary(self, user_id: str, secondary: str) -> Member3GuardianRecord | None:
        with self._sessions() as session:
            return session.scalar(select(Member3GuardianRecord).where(
                Member3GuardianRecord.record_type == self._record_type,
                Member3GuardianRecord.user_id == user_id,
                Member3GuardianRecord.secondary_key == secondary,
            ))

    def _list_rows(self, user_id: str) -> list[Member3GuardianRecord]:
        with self._sessions() as session:
            return list(session.scalars(select(Member3GuardianRecord).where(
                Member3GuardianRecord.record_type == self._record_type,
                Member3GuardianRecord.user_id == user_id,
            ).order_by(Member3GuardianRecord.updated_at.desc(), Member3GuardianRecord.record_id.desc())))

    def _delete(self, record_id: str) -> None:
        with self._sessions.begin() as session:
            session.execute(delete(Member3GuardianRecord).where(
                Member3GuardianRecord.record_type == self._record_type,
                Member3GuardianRecord.record_id == record_id,
            ))

    def delete_for_user(self, user_id: str) -> int:
        with self._sessions.begin() as session:
            result = session.execute(delete(Member3GuardianRecord).where(
                Member3GuardianRecord.record_type == self._record_type,
                Member3GuardianRecord.user_id == user_id,
            ))
            return result.rowcount or 0

    def _list_models(self, user_id: str) -> list[ModelT]:
        return [self._model.model_validate_json(row.payload) for row in self._list_rows(user_id)]


class SqlInsightRepository(_JsonRepository):
    def __init__(self, sessions: sessionmaker[Session]): super().__init__(sessions, "insight", InsightRecord)
    def save(self, record: InsightRecord): self._save(record.insight_id, record.user_id, record, record.source_event_id)
    def get(self, insight_id: str): return self._get(insight_id)
    def get_by_source(self, user_id: str, source_event_id: str):
        row = self._get_row_by_secondary(user_id, source_event_id)
        return InsightRecord.model_validate_json(row.payload) if row else None
    def list_for_user(self, user_id: str): return self._list_models(user_id)


class SqlEmergencyRepository(_JsonRepository):
    def __init__(self, sessions: sessionmaker[Session]): super().__init__(sessions, "emergency", EmergencyWorkflowRecord)
    def save(self, record: EmergencyWorkflowRecord): self._save(record.workflow_id, record.user_id, record, record.alert_id)
    def get(self, workflow_id: str): return self._get(workflow_id)
    def get_by_alert(self, user_id: str, alert_id: str):
        row = self._get_row_by_secondary(user_id, alert_id)
        return EmergencyWorkflowRecord.model_validate_json(row.payload) if row else None
    def list_for_user(self, user_id: str): return self._list_models(user_id)


class SqlNotificationRepository(_JsonRepository):
    def __init__(self, sessions: sessionmaker[Session]): super().__init__(sessions, "notification", NotificationRecord)
    @staticmethod
    def _key(source_event_id: str, channel: NotificationChannel) -> str: return f"{source_event_id}|{channel.value}"
    def save(self, record: NotificationRecord): self._save(record.notification_id, record.user_id, record, self._key(record.source_event_id, record.channel))
    def get(self, notification_id: str): return self._get(notification_id)
    def get_by_source(self, user_id: str, source_event_id: str, channel: NotificationChannel):
        row = self._get_row_by_secondary(user_id, self._key(source_event_id, channel))
        return NotificationRecord.model_validate_json(row.payload) if row else None
    def list_for_user(self, user_id: str): return self._list_models(user_id)


class SqlConversationRepository(_JsonRepository):
    def __init__(self, sessions: sessionmaker[Session]): super().__init__(sessions, "conversation", ConversationRecord)
    def save(self, record: ConversationRecord): self._save(record.conversation_id, record.user_id, record)
    def get(self, conversation_id: str): return self._get(conversation_id)
    def get_by_message(self, user_id: str, message_id: str):
        return next((record for record in self._list_models(user_id) if any(turn.message_id == message_id for turn in record.turns)), None)
    def list_for_user(self, user_id: str): return self._list_models(user_id)
    def delete(self, conversation_id: str): self._delete(conversation_id)


class SqlAlertRepository(_JsonRepository):
    def __init__(self, sessions: sessionmaker[Session]): super().__init__(sessions, "alert", AlertRecord)
    def save(self, stored: _StoredAlert): self._save(stored.record.alert_id, stored.record.user_id, stored.record, stored.record.event_id, stored.fingerprint)
    def get(self, alert_id: str):
        with self._sessions() as session:
            row = session.scalar(select(Member3GuardianRecord).where(Member3GuardianRecord.record_type == self._record_type, Member3GuardianRecord.record_id == alert_id))
            return _StoredAlert(AlertRecord.model_validate_json(row.payload), row.metadata_value or "") if row else None
    def get_by_event(self, user_id: str, event_id: str):
        row = self._get_row_by_secondary(user_id, event_id)
        return _StoredAlert(AlertRecord.model_validate_json(row.payload), row.metadata_value or "") if row else None
    def list_for_user(self, user_id: str):
        return [_StoredAlert(AlertRecord.model_validate_json(row.payload), row.metadata_value or "") for row in self._list_rows(user_id)]


class SqlCaregiverRepository(_JsonRepository):
    def __init__(self, sessions: sessionmaker[Session]):
        super().__init__(sessions, "caregiver", CaregiverLink)

    def save(self, link: CaregiverLink) -> None:
        self._save(link.link_id, link.user_id, link, link.caregiver_user_ref)

    def get(self, link_id: str) -> CaregiverLink | None:
        return self._get(link_id)

    def get_by_pair(self, user_id: str, caregiver_user_ref: str) -> CaregiverLink | None:
        row = self._get_row_by_secondary(user_id, caregiver_user_ref)
        return CaregiverLink.model_validate_json(row.payload) if row else None

    def list_for_user(self, user_id: str) -> list[CaregiverLink]:
        return self._list_models(user_id)


class SqlGuardianOrchestrationRepository(_JsonRepository):
    def __init__(self, sessions: sessionmaker[Session]):
        super().__init__(sessions, "orchestration", GuardianProcessResponse)

    def save(self, record: GuardianProcessResponse) -> None:
        self._save(f"{record.user_id}:{record.event_id}", record.user_id, record, record.event_id)

    def get(self, user_id: str, event_id: str) -> GuardianProcessResponse | None:
        row = self._get_row_by_secondary(user_id, event_id)
        return GuardianProcessResponse.model_validate_json(row.payload) if row else None

    def list_for_user(self, user_id: str) -> list[GuardianProcessResponse]:
        return self._list_models(user_id)

    def delete_for_user(self, user_id: str) -> int:
        return super().delete_for_user(user_id)
