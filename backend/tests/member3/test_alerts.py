"""Offline unit and API tests for the Member 3 alert system."""

from datetime import datetime, timedelta, timezone
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.member3.alerts import get_alert_service, router
from app.schemas.member3.alerts import AlertEvaluationRequest, AlertPriority, AlertStatus
from app.services.member3.guardian.alert_service import (
    AlertNotFoundError,
    AlertService,
    InMemoryAlertRepository,
    InvalidAlertTransitionError,
)
from ml.safety import SafetyAction


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now


def make_request(event_id="event-1", action=SafetyAction.RE_MEASURE, **updates):
    values = dict(
        user_id="user-1",
        event_id=event_id,
        safety_action=action,
        safety_reason="Upstream safety decision",
        evidence=["Low signal quality"],
        occurred_at=datetime(2026, 8, 30, 11, tzinfo=timezone.utc),
    )
    values.update(updates)
    return AlertEvaluationRequest(**values)


class AlertSchemaTests(unittest.TestCase):
    def test_required_strings_are_trimmed(self):
        request = make_request(user_id=" user-1 ", event_id=" event-1 ")
        self.assertEqual(request.user_id, "user-1")
        self.assertEqual(request.event_id, "event-1")

    def test_blank_identifiers_are_rejected(self):
        for field in ("user_id", "event_id", "safety_reason"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                make_request(**{field: "   "})

    def test_evidence_is_trimmed_and_deduplicated(self):
        request = make_request(evidence=[" Low quality ", "low QUALITY"])
        self.assertEqual(request.evidence, ["Low quality"])

    def test_empty_evidence_is_rejected(self):
        with self.assertRaises(ValidationError):
            make_request(evidence=[])


class AlertServiceTests(unittest.TestCase):
    def setUp(self):
        self.clock = MutableClock()
        self.service = AlertService(clock=self.clock)

    def test_normal_and_observe_do_not_create_alerts(self):
        for action in (SafetyAction.NORMAL, SafetyAction.OBSERVE):
            with self.subTest(action=action):
                result = self.service.evaluate(make_request(action=action, event_id=action.value))
                self.assertFalse(result.created)
                self.assertEqual(result.suppressed_reason, "action_does_not_require_alert")

    def test_priority_mapping_for_alert_actions(self):
        cases = {
            SafetyAction.SELF_CARE: AlertPriority.LOW,
            SafetyAction.RE_MEASURE: AlertPriority.MEDIUM,
            SafetyAction.CAREGIVER_ALERT: AlertPriority.HIGH,
            SafetyAction.EMERGENCY_ESCALATION: AlertPriority.CRITICAL,
        }
        for index, (action, priority) in enumerate(cases.items()):
            with self.subTest(action=action):
                result = self.service.evaluate(make_request(event_id=f"e-{index}", action=action))
                self.assertTrue(result.created)
                self.assertEqual(result.alert.priority, priority)

    def test_same_event_is_idempotently_suppressed(self):
        self.assertTrue(self.service.evaluate(make_request()).created)
        result = self.service.evaluate(make_request())
        self.assertFalse(result.created)
        self.assertEqual(result.suppressed_reason, "event_already_processed")

    def test_duplicate_fingerprint_within_cooldown_is_suppressed(self):
        self.service.evaluate(make_request(event_id="e1"))
        result = self.service.evaluate(make_request(event_id="e2"))
        self.assertEqual(result.suppressed_reason, "duplicate_within_cooldown")

    def test_duplicate_after_cooldown_is_created(self):
        self.service.evaluate(make_request(event_id="e1"))
        self.clock.now += timedelta(minutes=31)
        self.assertTrue(self.service.evaluate(make_request(event_id="e2")).created)

    def test_different_users_are_not_deduplicated(self):
        self.service.evaluate(make_request(event_id="e1", user_id="u1"))
        self.assertTrue(self.service.evaluate(make_request(event_id="e2", user_id="u2")).created)

    def test_event_idempotency_is_scoped_to_user(self):
        self.assertTrue(
            self.service.evaluate(make_request(event_id="shared", user_id="u1")).created
        )
        self.assertTrue(
            self.service.evaluate(make_request(event_id="shared", user_id="u2")).created
        )

    def test_alert_history_is_newest_first(self):
        self.service.evaluate(make_request(event_id="e1"))
        self.clock.now += timedelta(minutes=31)
        second = self.service.evaluate(make_request(event_id="e2"))
        history = self.service.list_alerts("user-1")
        self.assertEqual(history.alerts[0].alert_id, second.alert.alert_id)
        self.assertEqual(history.count, 2)

    def test_acknowledge_then_resolve(self):
        alert = self.service.evaluate(make_request()).alert
        acknowledged = self.service.update_status(alert.alert_id, AlertStatus.ACKNOWLEDGED)
        resolved = self.service.update_status(alert.alert_id, AlertStatus.RESOLVED)
        self.assertEqual(acknowledged.status, AlertStatus.ACKNOWLEDGED)
        self.assertEqual(resolved.status, AlertStatus.RESOLVED)

    def test_invalid_transition_is_rejected(self):
        alert = self.service.evaluate(make_request()).alert
        self.service.update_status(alert.alert_id, AlertStatus.RESOLVED)
        with self.assertRaises(InvalidAlertTransitionError):
            self.service.update_status(alert.alert_id, AlertStatus.ACKNOWLEDGED)

    def test_critical_alert_cannot_be_dismissed(self):
        alert = self.service.evaluate(make_request(action=SafetyAction.EMERGENCY_ESCALATION)).alert
        with self.assertRaises(InvalidAlertTransitionError):
            self.service.update_status(alert.alert_id, AlertStatus.DISMISSED)

    def test_missing_alert_raises(self):
        with self.assertRaises(AlertNotFoundError):
            self.service.update_status("missing", AlertStatus.RESOLVED)


class AlertApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.service = AlertService(repository=InMemoryAlertRepository())
        self.app.dependency_overrides[get_alert_service] = lambda: self.service
        self.client = TestClient(self.app)

    def payload(self, action="re_measure"):
        return {
            "user_id": "api-user",
            "event_id": "api-event",
            "safety_action": action,
            "safety_reason": "Low signal quality",
            "evidence": ["Motion artifact"],
            "occurred_at": "2026-08-30T11:00:00Z",
        }

    def test_evaluate_list_and_acknowledge(self):
        created = self.client.post("/api/v1/member3/alerts/evaluate", json=self.payload())
        self.assertEqual(created.status_code, 200)
        alert_id = created.json()["alert"]["alert_id"]
        listed = self.client.get("/api/v1/member3/alerts", params={"user_id": "api-user"})
        self.assertEqual(listed.json()["count"], 1)
        updated = self.client.patch(
            f"/api/v1/member3/alerts/{alert_id}/status",
            json={"status": "acknowledged"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "acknowledged")

    def test_unknown_alert_returns_404(self):
        response = self.client.patch(
            "/api/v1/member3/alerts/missing/status", json={"status": "resolved"}
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_transition_returns_409(self):
        created = self.client.post(
            "/api/v1/member3/alerts/evaluate",
            json=self.payload(action="emergency_escalation"),
        )
        alert_id = created.json()["alert"]["alert_id"]
        response = self.client.patch(
            f"/api/v1/member3/alerts/{alert_id}/status",
            json={"status": "dismissed"},
        )
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
