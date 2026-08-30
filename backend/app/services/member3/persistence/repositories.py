"""Synchronous SQLAlchemy adapters for the existing Member 3 services."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.member3.guardian_record import Member3GuardianRecord
from app.schemas.member3.alerts import AlertRecord
from app.schemas.member3.conversations import ConversationRecord
from app.schemas.member3.emergency import EmergencyWorkflowRecord
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
    def __init__(self, sessions): super().__init__(sessions, "insight", InsightRecord)
    def save(self, record): self._save(record.insight_id, record.user_id, record, record.source_event_id)
    def get(self, insight_id): return self._get(insight_id)
    def get_by_source(self, user_id, source_event_id):
        row = self._get_row_by_secondary(user_id, source_event_id)
        return InsightRecord.model_validate_json(row.payload) if row else None
    def list_for_user(self, user_id): return self._list_models(user_id)


class SqlEmergencyRepository(_JsonRepository):
    def __init__(self, sessions): super().__init__(sessions, "emergency", EmergencyWorkflowRecord)
    def save(self, record): self._save(record.workflow_id, record.user_id, record, record.alert_id)
    def get(self, workflow_id): return self._get(workflow_id)
    def get_by_alert(self, user_id, alert_id):
        row = self._get_row_by_secondary(user_id, alert_id)
        return EmergencyWorkflowRecord.model_validate_json(row.payload) if row else None
    def list_for_user(self, user_id): return self._list_models(user_id)


class SqlNotificationRepository(_JsonRepository):
    def __init__(self, sessions): super().__init__(sessions, "notification", NotificationRecord)
    @staticmethod
    def _key(source_event_id, channel): return f"{source_event_id}|{channel.value}"
    def save(self, record): self._save(record.notification_id, record.user_id, record, self._key(record.source_event_id, record.channel))
    def get(self, notification_id): return self._get(notification_id)
    def get_by_source(self, user_id, source_event_id, channel):
        row = self._get_row_by_secondary(user_id, self._key(source_event_id, channel))
        return NotificationRecord.model_validate_json(row.payload) if row else None
    def list_for_user(self, user_id): return self._list_models(user_id)


class SqlConversationRepository(_JsonRepository):
    def __init__(self, sessions): super().__init__(sessions, "conversation", ConversationRecord)
    def save(self, record): self._save(record.conversation_id, record.user_id, record)
    def get(self, conversation_id): return self._get(conversation_id)
    def get_by_message(self, user_id, message_id):
        return next((record for record in self._list_models(user_id) if any(turn.message_id == message_id for turn in record.turns)), None)
    def list_for_user(self, user_id): return self._list_models(user_id)
    def delete(self, conversation_id): self._delete(conversation_id)


class SqlAlertRepository(_JsonRepository):
    def __init__(self, sessions): super().__init__(sessions, "alert", AlertRecord)
    def save(self, stored): self._save(stored.record.alert_id, stored.record.user_id, stored.record, stored.record.event_id, stored.fingerprint)
    def get(self, alert_id):
        with self._sessions() as session:
            row = session.scalar(select(Member3GuardianRecord).where(Member3GuardianRecord.record_type == self._record_type, Member3GuardianRecord.record_id == alert_id))
            return _StoredAlert(AlertRecord.model_validate_json(row.payload), row.metadata_value or "") if row else None
    def get_by_event(self, user_id, event_id):
        row = self._get_row_by_secondary(user_id, event_id)
        return _StoredAlert(AlertRecord.model_validate_json(row.payload), row.metadata_value or "") if row else None
    def list_for_user(self, user_id):
        return [_StoredAlert(AlertRecord.model_validate_json(row.payload), row.metadata_value or "") for row in self._list_rows(user_id)]
