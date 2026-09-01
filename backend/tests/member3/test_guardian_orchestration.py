"""Integration-contract tests for the complete Member 3 backend loop."""

from datetime import datetime, timezone
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.member3.guardian import get_guardian_service, router
from app.schemas.member3.assistant import EvidenceItem
from app.schemas.member3.guardian import GuardianProcessRequest
from app.services.member3.guardian.orchestration_service import GuardianOrchestrationService
from ml.safety import SafetyAction


def request(**updates):
    values = dict(
        user_id="user-1",
        event_id="event-1",
        insight_type="recovery",
        deviation_score=1.8,
        confidence=0.9,
        signal_quality=0.9,
        evidence=[EvidenceItem(
            metric="sleep",
            current_value=5.5,
            baseline_value=7.2,
            unit="hours",
            direction="below baseline",
            confidence=0.9,
            signal_quality=0.9,
        )],
        occurred_at=datetime(2026, 8, 30, 12, tzinfo=timezone.utc),
    )
    values.update(updates)
    return GuardianProcessRequest(**values)


class GuardianOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.service = GuardianOrchestrationService()

    def test_normal_creates_insight_but_no_alert_or_notification(self):
        result = self.service.process(request(deviation_score=0))
        self.assertEqual(result.safety_action, SafetyAction.NORMAL)
        self.assertFalse(result.alert.created)
        self.assertIsNone(result.notifications)
        self.assertIsNone(result.emergency_workflow)

    def test_self_care_creates_insight_alert_and_notification(self):
        result = self.service.process(request())
        self.assertEqual(result.safety_action, SafetyAction.SELF_CARE)
        self.assertTrue(result.alert.created)
        self.assertEqual(result.notifications.count, 1)
        self.assertIsNone(result.emergency_workflow)

    def test_low_quality_forces_remeasurement_path(self):
        result = self.service.process(request(deviation_score=3, signal_quality=0.2))
        self.assertEqual(result.safety_action, SafetyAction.RE_MEASURE)
        self.assertTrue(result.alert.created)

    def test_confirmed_severe_symptoms_create_full_emergency_path(self):
        result = self.service.process(
            request(
                deviation_score=0,
                confidence=0.1,
                signal_quality=0.1,
                user_confirmed_severe_symptoms=True,
                caregiver_contact_id="caregiver-1",
            )
        )
        self.assertEqual(result.safety_action, SafetyAction.EMERGENCY_ESCALATION)
        self.assertTrue(result.alert.created)
        self.assertEqual(result.notifications.count, 1)
        self.assertIsNotNone(result.emergency_workflow)
        self.assertFalse(result.emergency_workflow.external_action_performed)

    def test_high_confidence_critical_flag_creates_emergency_path(self):
        result = self.service.process(
            request(critical_flags=["validated critical pattern"])
        )
        self.assertEqual(result.safety_action, SafetyAction.EMERGENCY_ESCALATION)

    def test_processing_is_idempotent(self):
        first = self.service.process(request())
        second = self.service.process(request())
        self.assertEqual(first, second)

    def test_decision_trace_is_stable_and_minimizes_sensitive_data(self):
        first = self.service.process(request(critical_flags=["validated critical pattern"]))
        second = self.service.process(request(critical_flags=["validated critical pattern"]))

        trace = first.decision_trace
        self.assertEqual(trace, second.decision_trace)
        self.assertEqual(trace.policy_version, "member3-safety-rules-v1")
        self.assertEqual(trace.source_event_id, "event-1")
        self.assertEqual(trace.evidence_metrics, ("sleep",))
        self.assertEqual(trace.critical_flags_count, 1)
        self.assertNotIn("caregiver", trace.model_dump_json().lower())

    def test_idempotency_is_user_scoped(self):
        first = self.service.process(request(user_id="u1"))
        second = self.service.process(request(user_id="u2"))
        self.assertNotEqual(first.insight.insight_id, second.insight.insight_id)

    def test_unconsented_channel_is_suppressed(self):
        result = self.service.process(
            request(
                notification_channels=["sms"],
                consented_channels=[],
                channel_targets={"sms": "opaque-phone-ref"},
            )
        )
        self.assertEqual(result.notifications.count, 0)
        self.assertEqual(
            result.notifications.suppressed_channels["sms"], "channel_not_consented"
        )

    def test_safety_action_is_preserved_across_outputs(self):
        result = self.service.process(request(deviation_score=2.8))
        self.assertEqual(result.insight.safety_action, result.safety_action)
        self.assertEqual(result.alert.alert.safety_action, result.safety_action)

    def test_evidence_is_not_invented(self):
        result = self.service.process(request())
        self.assertEqual([item.metric for item in result.insight.evidence], ["sleep"])


class GuardianApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.service = GuardianOrchestrationService()
        self.app.dependency_overrides[get_guardian_service] = lambda: self.service
        self.client = TestClient(self.app)

    def payload(self):
        return request().model_dump(mode="json")

    def test_full_process_endpoint(self):
        response = self.client.post("/api/v1/member3/guardian/process", json=self.payload())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["safety_action"], "self_care")
        self.assertIsNotNone(body["insight"])
        self.assertTrue(body["alert"]["created"])
        self.assertEqual(body["decision_trace"]["policy_version"], "member3-safety-rules-v1")

    def test_invalid_fraction_returns_422(self):
        payload = self.payload()
        payload["confidence"] = 1.1
        self.assertEqual(
            self.client.post("/api/v1/member3/guardian/process", json=payload).status_code,
            422,
        )


if __name__ == "__main__":
    unittest.main()
