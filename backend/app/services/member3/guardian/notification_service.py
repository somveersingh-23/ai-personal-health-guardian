"""Consent-aware notification intent tracking without external delivery claims."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Callable

from app.schemas.member3.notifications import (
    DeliveryOutcome,
    DeliveryReceiptRequest,
    NotificationBatchResponse,
    NotificationChannel,
    NotificationCreateRequest,
    NotificationListResponse,
    NotificationRecord,
    NotificationStatus,
    new_notification_id,
)


class NotificationNotFoundError(LookupError):
    pass


class InvalidNotificationTransitionError(ValueError):
    pass


class NotificationRetryLimitError(ValueError):
    pass


class InMemoryNotificationRepository:
    def __init__(self) -> None:
        self._records: dict[str, NotificationRecord] = {}
        self._source_index: dict[tuple[str, str, NotificationChannel], str] = {}
        self._lock = RLock()

    def save(self, record: NotificationRecord) -> None:
        with self._lock:
            self._records[record.notification_id] = record
            self._source_index[
                (record.user_id, record.source_event_id, record.channel)
            ] = record.notification_id

    def get(self, notification_id: str) -> NotificationRecord | None:
        with self._lock:
            return self._records.get(notification_id)

    def get_by_source(
        self, user_id: str, source_event_id: str, channel: NotificationChannel
    ) -> NotificationRecord | None:
        with self._lock:
            record_id = self._source_index.get((user_id, source_event_id, channel))
            return self._records.get(record_id) if record_id else None

    def list_for_user(self, user_id: str) -> list[NotificationRecord]:
        with self._lock:
            records = [item for item in self._records.values() if item.user_id == user_id]
        return sorted(records, key=lambda item: (item.created_at, item.notification_id), reverse=True)

    def delete_for_user(self, user_id: str) -> int:
        with self._lock:
            ids = [key for key, item in self._records.items() if item.user_id == user_id]
            for key in ids:
                item = self._records.pop(key)
                self._source_index.pop((item.user_id, item.source_event_id, item.channel), None)
            return len(ids)


class NotificationService:
    MAX_ATTEMPTS = 3

    def __init__(
        self,
        repository: InMemoryNotificationRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository or InMemoryNotificationRepository()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create(self, request: NotificationCreateRequest) -> NotificationBatchResponse:
        created: list[NotificationRecord] = []
        suppressed: dict[str, str] = {}
        consented = set(request.consented_channels)
        now = self._utc(self._clock())

        for channel in request.channels:
            if channel not in consented:
                suppressed[channel.value] = "channel_not_consented"
                continue
            if channel != NotificationChannel.IN_APP and channel not in request.channel_targets:
                suppressed[channel.value] = "missing_opaque_target_reference"
                continue
            existing = self._repository.get_by_source(
                request.user_id, request.source_event_id, channel
            )
            if existing is not None:
                created.append(existing)
                continue
            record = NotificationRecord(
                notification_id=new_notification_id(),
                user_id=request.user_id,
                source_event_id=request.source_event_id,
                title=request.title,
                body=request.body,
                priority=request.priority,
                channel=channel,
                target_ref=request.channel_targets.get(channel),
                status=NotificationStatus.QUEUED,
                attempt_count=0,
                provider_receipt_id=None,
                failure_reason=None,
                created_at=now,
                updated_at=now,
            )
            self._repository.save(record)
            created.append(record)

        return NotificationBatchResponse(
            notifications=created,
            suppressed_channels=suppressed,
            count=len(created),
        )

    def request_dispatch(
        self, notification_id: str, user_id: str | None = None
    ) -> NotificationRecord:
        current = self._get_owned_or_trusted(notification_id, user_id)
        if current.status != NotificationStatus.QUEUED:
            raise InvalidNotificationTransitionError(
                f"Cannot request dispatch while status is {current.status.value}"
            )
        if current.attempt_count >= self.MAX_ATTEMPTS:
            raise NotificationRetryLimitError("Notification retry limit reached")
        updated = current.model_copy(
            update={
                "status": NotificationStatus.DISPATCH_REQUESTED,
                "attempt_count": current.attempt_count + 1,
                "updated_at": self._utc(self._clock()),
                "failure_reason": None,
            }
        )
        self._repository.save(updated)
        return updated

    def record_receipt(
        self,
        notification_id: str,
        receipt: DeliveryReceiptRequest,
        user_id: str | None = None,
    ) -> NotificationRecord:
        current = self._get_owned_or_trusted(notification_id, user_id)
        if current.status != NotificationStatus.DISPATCH_REQUESTED:
            raise InvalidNotificationTransitionError(
                "A delivery receipt requires dispatch_requested status"
            )
        status = (
            NotificationStatus.DELIVERED
            if receipt.outcome == DeliveryOutcome.DELIVERED
            else NotificationStatus.FAILED
        )
        updated = current.model_copy(
            update={
                "status": status,
                "provider_receipt_id": receipt.provider_receipt_id,
                "failure_reason": receipt.failure_reason,
                "updated_at": self._utc(self._clock()),
            }
        )
        self._repository.save(updated)
        return updated

    def retry(self, notification_id: str, user_id: str | None = None) -> NotificationRecord:
        current = self._get_owned_or_trusted(notification_id, user_id)
        if current.status != NotificationStatus.FAILED:
            raise InvalidNotificationTransitionError("Only failed notifications can retry")
        if current.attempt_count >= self.MAX_ATTEMPTS:
            raise NotificationRetryLimitError("Notification retry limit reached")
        updated = current.model_copy(
            update={
                "status": NotificationStatus.QUEUED,
                "provider_receipt_id": None,
                "failure_reason": None,
                "updated_at": self._utc(self._clock()),
            }
        )
        self._repository.save(updated)
        return updated

    def cancel(self, notification_id: str, user_id: str | None = None) -> NotificationRecord:
        current = self._get_owned_or_trusted(notification_id, user_id)
        if current.status not in {NotificationStatus.QUEUED, NotificationStatus.FAILED}:
            raise InvalidNotificationTransitionError(
                f"Cannot cancel notification while status is {current.status.value}"
            )
        updated = current.model_copy(
            update={
                "status": NotificationStatus.CANCELLED,
                "updated_at": self._utc(self._clock()),
            }
        )
        self._repository.save(updated)
        return updated

    def get(self, notification_id: str) -> NotificationRecord:
        record = self._repository.get(" ".join(notification_id.split()))
        if record is None:
            raise NotificationNotFoundError("Notification not found")
        return record

    def get_for_user(self, notification_id: str, user_id: str) -> NotificationRecord:
        record = self.get(notification_id)
        if record.user_id != " ".join(user_id.split()):
            # Do not reveal another user's notification identifier.
            raise NotificationNotFoundError("Notification not found")
        return record

    def _get_owned_or_trusted(
        self, notification_id: str, user_id: str | None
    ) -> NotificationRecord:
        return self.get(notification_id) if user_id is None else self.get_for_user(notification_id, user_id)

    def list_notifications(self, user_id: str) -> NotificationListResponse:
        cleaned = " ".join(user_id.split())
        if not cleaned:
            raise ValueError("user_id must not be blank")
        records = self._repository.list_for_user(cleaned)
        return NotificationListResponse(
            user_id=cleaned, notifications=records, count=len(records)
        )

    def purge_user(self, user_id: str) -> int:
        return self._repository.delete_for_user(" ".join(user_id.split()))

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
