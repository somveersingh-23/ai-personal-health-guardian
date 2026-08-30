"""In-memory, user-scoped AI Guardian conversation management."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Callable

from app.schemas.member3.assistant import ExplainRequest
from app.schemas.member3.conversations import (
    ConversationDeleteResponse,
    ConversationListResponse,
    ConversationMessageRequest,
    ConversationRecord,
    ConversationTurn,
    new_conversation_id,
)
from app.services.member3.guardian.explanation_service import ExplanationService


class ConversationNotFoundError(LookupError):
    pass


class ConversationOwnershipError(PermissionError):
    pass


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._records: dict[str, ConversationRecord] = {}
        self._message_index: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def save(self, record: ConversationRecord) -> None:
        with self._lock:
            self._records[record.conversation_id] = record
            for turn in record.turns:
                self._message_index[(record.user_id, turn.message_id)] = record.conversation_id

    def get(self, conversation_id: str) -> ConversationRecord | None:
        with self._lock:
            return self._records.get(conversation_id)

    def get_by_message(self, user_id: str, message_id: str) -> ConversationRecord | None:
        with self._lock:
            conversation_id = self._message_index.get((user_id, message_id))
            return self._records.get(conversation_id) if conversation_id else None

    def list_for_user(self, user_id: str) -> list[ConversationRecord]:
        with self._lock:
            records = [record for record in self._records.values() if record.user_id == user_id]
        return sorted(records, key=lambda record: (record.updated_at, record.conversation_id), reverse=True)

    def delete(self, conversation_id: str) -> None:
        with self._lock:
            record = self._records.pop(conversation_id)
            for turn in record.turns:
                self._message_index.pop((record.user_id, turn.message_id), None)


class ConversationService:
    def __init__(
        self,
        explanation_service: ExplanationService | None = None,
        repository: InMemoryConversationRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._explanation = explanation_service or ExplanationService()
        self._repository = repository or InMemoryConversationRepository()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def send(self, request: ConversationMessageRequest) -> ConversationRecord:
        existing_message = self._repository.get_by_message(request.user_id, request.message_id)
        if existing_message is not None:
            return existing_message
        now = self._utc(self._clock())
        if request.conversation_id:
            current = self._owned(request.conversation_id, request.user_id)
        else:
            current = ConversationRecord(
                conversation_id=new_conversation_id(),
                user_id=request.user_id,
                turns=(),
                created_at=now,
                updated_at=now,
            )
        explanation = self._explanation.explain(
            ExplainRequest(
                user_id=request.user_id,
                question=request.question,
                evidence=request.evidence,
                safety_action=request.safety_action.value,
                safety_reason=request.safety_reason,
                conversation_id=current.conversation_id,
                locale=request.locale,
            )
        )
        turn = ConversationTurn(
            message_id=request.message_id,
            question=request.question,
            answer=explanation.answer,
            safety_action=request.safety_action,
            evidence_metrics=tuple(explanation.evidence_used),
            disclaimer=explanation.disclaimer,
            created_at=now,
        )
        updated = current.model_copy(
            update={"turns": (*current.turns, turn), "updated_at": now}
        )
        self._repository.save(updated)
        return updated

    def get(self, conversation_id: str, user_id: str) -> ConversationRecord:
        return self._owned(conversation_id, user_id)

    def list_conversations(self, user_id: str) -> ConversationListResponse:
        cleaned = _required(user_id, "user_id")
        records = self._repository.list_for_user(cleaned)
        return ConversationListResponse(user_id=cleaned, conversations=records, count=len(records))

    def delete(self, conversation_id: str, user_id: str) -> ConversationDeleteResponse:
        record = self._owned(conversation_id, user_id)
        self._repository.delete(record.conversation_id)
        return ConversationDeleteResponse(conversation_id=record.conversation_id, deleted=True)

    def _owned(self, conversation_id: str, user_id: str) -> ConversationRecord:
        record = self._repository.get(_required(conversation_id, "conversation_id"))
        if record is None:
            raise ConversationNotFoundError("Conversation not found")
        if record.user_id != _required(user_id, "user_id"):
            raise ConversationOwnershipError("Conversation does not belong to this user")
        return record

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def _required(value: str, label: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned
