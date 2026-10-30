from app.schemas.member3.notifications import DeliveryOutcome, DeliveryReceiptRequest, NotificationChannel
from app.services.member3.connectors.base import NotificationConnector
from app.services.member3.guardian.notification_service import NotificationService


class NotificationDispatcher:
    def __init__(self, service: NotificationService, connectors: dict[NotificationChannel, NotificationConnector]):
        self._service = service
        self._connectors = dict(connectors)

    def dispatch(self, notification_id: str):
        pending = self._service.request_dispatch(notification_id)
        connector = self._connectors.get(pending.channel)
        if connector is None:
            result_reason = f"No connector configured for {pending.channel.value}"
            return self._service.record_receipt(notification_id, DeliveryReceiptRequest(outcome=DeliveryOutcome.FAILED, failure_reason=result_reason))
        result = connector.send(pending)
        receipt = DeliveryReceiptRequest(
            outcome=DeliveryOutcome.DELIVERED if result.delivered else DeliveryOutcome.FAILED,
            provider_receipt_id=result.receipt_id,
            failure_reason=result.failure_reason,
        )
        return self._service.record_receipt(notification_id, receipt)
