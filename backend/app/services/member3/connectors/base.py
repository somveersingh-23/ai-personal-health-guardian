from dataclasses import dataclass
from typing import Protocol

from app.schemas.member3.notifications import NotificationRecord


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    receipt_id: str | None = None
    failure_reason: str | None = None


class NotificationConnector(Protocol):
    def send(self, notification: NotificationRecord) -> DeliveryResult: ...
