"""Offline tests for notification intent and receipt tracking."""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.member3.notifications import get_notification_service, router
from app.schemas.member3.alerts import AlertPriority
from app.schemas.member3.notifications import (
    DeliveryOutcome,
    DeliveryReceiptRequest,
    NotificationChannel,
    NotificationCreateRequest,
    NotificationStatus,
)
from app.services.member3.guardian.notification_service import (
    InMemoryNotificationRepository,
    InvalidNotificationTransitionError,
    NotificationRetryLimitError,
    NotificationService,
)


def create_request(**updates):
    values = dict(
        user_id="user-1",
        source_event_id="event-1",
        title="Health alert",
        body="Review your latest health insight.",
        priority=AlertPriority.HIGH,
        channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH],
        consented_channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH],
        channel_targets={NotificationChannel.PUSH: "device-token-ref-1"},
    )
    values.update(updates)
    return NotificationCreateRequest(**values)


class NotificationSchemaTests(unittest.TestCase):
    def test_strings_are_trimmed(self):
        request = create_request(user_id=" user-1 ", title=" Alert ")
        self.assertEqual(request.user_id, "user-1")
        self.assertEqual(request.title, "Alert")

    def test_blank_content_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_request(body="   ")

    def test_duplicate_channels_are_removed(self):
        request = create_request(channels=[NotificationChannel.IN_APP] * 2)
        self.assertEqual(request.channels, [NotificationChannel.IN_APP])

    def test_delivered_receipt_requires_provider_id(self):
        with self.assertRaises(ValidationError):
            DeliveryReceiptRequest(outcome=DeliveryOutcome.DELIVERED)

    def test_failed_receipt_requires_reason(self):
        with self.assertRaises(ValidationError):
            DeliveryReceiptRequest(outcome=DeliveryOutcome.FAILED)


class NotificationServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = NotificationService()

    def test_consented_channels_are_queued(self):
        result = self.service.create(create_request())
        self.assertEqual(result.count, 2)
        self.assertTrue(all(item.status == NotificationStatus.QUEUED for item in result.notifications))

    def test_unconsented_channel_is_suppressed_even_when_critical(self):
        request = create_request(
            priority=AlertPriority.CRITICAL,
            channels=[NotificationChannel.SMS],
            consented_channels=[],
            channel_targets={NotificationChannel.SMS: "phone-ref"},
        )
        result = self.service.create(request)
        self.assertEqual(result.count, 0)
        self.assertEqual(result.suppressed_channels["sms"], "channel_not_consented")

    def test_external_channel_requires_opaque_target(self):
        result = self.service.create(
            create_request(
                channels=[NotificationChannel.PUSH],
                consented_channels=[NotificationChannel.PUSH],
                channel_targets={},
            )
        )
        self.assertEqual(result.suppressed_channels["push"], "missing_opaque_target_reference")

    def test_creation_is_idempotent_per_user_event_and_channel(self):
        first = self.service.create(create_request())
        second = self.service.create(create_request())
        self.assertEqual(
            [item.notification_id for item in first.notifications],
            [item.notification_id for item in second.notifications],
        )

    def test_idempotency_is_user_scoped(self):
        first = self.service.create(create_request(user_id="u1"))
        second = self.service.create(create_request(user_id="u2"))
        self.assertNotEqual(first.notifications[0].notification_id, second.notifications[0].notification_id)

    def test_dispatch_does_not_claim_delivery(self):
        record = self.service.create(create_request(channels=[NotificationChannel.IN_APP])).notifications[0]
        dispatched = self.service.request_dispatch(record.notification_id)
        self.assertEqual(dispatched.status, NotificationStatus.DISPATCH_REQUESTED)
        self.assertIsNone(dispatched.provider_receipt_id)

    def test_delivery_requires_explicit_receipt(self):
        record = self.service.create(create_request(channels=[NotificationChannel.IN_APP])).notifications[0]
        record = self.service.request_dispatch(record.notification_id)
        delivered = self.service.record_receipt(
            record.notification_id,
            DeliveryReceiptRequest(
                outcome=DeliveryOutcome.DELIVERED,
                provider_receipt_id="receipt-1",
            ),
        )
        self.assertEqual(delivered.status, NotificationStatus.DELIVERED)

    def test_failed_delivery_can_retry(self):
        record = self.service.create(create_request(channels=[NotificationChannel.IN_APP])).notifications[0]
        record = self.service.request_dispatch(record.notification_id)
        record = self.service.record_receipt(
            record.notification_id,
            DeliveryReceiptRequest(outcome=DeliveryOutcome.FAILED, failure_reason="offline"),
        )
        retried = self.service.retry(record.notification_id)
        self.assertEqual(retried.status, NotificationStatus.QUEUED)

    def test_retry_limit_is_enforced(self):
        record = self.service.create(create_request(channels=[NotificationChannel.IN_APP])).notifications[0]
        for attempt in range(3):
            record = self.service.request_dispatch(record.notification_id)
            record = self.service.record_receipt(
                record.notification_id,
                DeliveryReceiptRequest(outcome=DeliveryOutcome.FAILED, failure_reason="offline"),
            )
            if attempt < 2:
                record = self.service.retry(record.notification_id)
        with self.assertRaises(NotificationRetryLimitError):
            self.service.retry(record.notification_id)

    def test_delivered_notification_cannot_cancel(self):
        record = self.service.create(create_request(channels=[NotificationChannel.IN_APP])).notifications[0]
        record = self.service.request_dispatch(record.notification_id)
        record = self.service.record_receipt(
            record.notification_id,
            DeliveryReceiptRequest(outcome=DeliveryOutcome.DELIVERED, provider_receipt_id="r"),
        )
        with self.assertRaises(InvalidNotificationTransitionError):
            self.service.cancel(record.notification_id)

    def test_list_is_user_scoped(self):
        self.service.create(create_request(user_id="u1"))
        self.service.create(create_request(user_id="u2"))
        self.assertEqual(self.service.list_notifications("u1").count, 2)


class NotificationApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.service = NotificationService(InMemoryNotificationRepository())
        self.app.dependency_overrides[get_notification_service] = lambda: self.service
        self.client = TestClient(self.app)

    def payload(self):
        return {
            "user_id": "api-user",
            "source_event_id": "api-event",
            "title": "Health alert",
            "body": "Review your health insight.",
            "priority": "high",
            "channels": ["in_app"],
            "consented_channels": ["in_app"],
            "channel_targets": {},
        }

    def test_create_dispatch_receipt_and_list(self):
        created = self.client.post("/api/v1/member3/notifications", json=self.payload())
        self.assertEqual(created.status_code, 200)
        notification_id = created.json()["notifications"][0]["notification_id"]
        dispatched = self.client.post(f"/api/v1/member3/notifications/{notification_id}/dispatch")
        self.assertEqual(dispatched.json()["status"], "dispatch_requested")
        receipt = self.client.post(
            f"/api/v1/member3/notifications/{notification_id}/receipt",
            json={"outcome": "delivered", "provider_receipt_id": "receipt-1"},
        )
        self.assertEqual(receipt.json()["status"], "delivered")
        listed = self.client.get(
            "/api/v1/member3/notifications", params={"user_id": "api-user"}
        )
        self.assertEqual(listed.json()["count"], 1)

    def test_missing_notification_returns_404(self):
        response = self.client.post("/api/v1/member3/notifications/missing/dispatch")
        self.assertEqual(response.status_code, 404)

    def test_invalid_transition_returns_409(self):
        created = self.client.post("/api/v1/member3/notifications", json=self.payload())
        notification_id = created.json()["notifications"][0]["notification_id"]
        response = self.client.post(
            f"/api/v1/member3/notifications/{notification_id}/receipt",
            json={"outcome": "delivered", "provider_receipt_id": "r"},
        )
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
