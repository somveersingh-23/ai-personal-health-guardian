"""Tests for structured Member 3 health insights."""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.member3.insights import get_insight_service, router
from app.schemas.member3.assistant import EvidenceItem
from app.schemas.member3.insights import InsightCreateRequest, InsightSeverity, InsightStatus
from app.services.member3.guardian.insight_service import (
    InMemoryInsightRepository,
    InsightService,
    InvalidInsightTransitionError,
)
from ml.safety import SafetyAction


def evidence(confidence=0.9, quality=0.9):
    return EvidenceItem(
        metric="sleep",
        current_value=5.5,
        baseline_value=7.2,
        unit="hours",
        direction="below baseline",
        confidence=confidence,
        signal_quality=quality,
    )


def request(action=SafetyAction.SELF_CARE, **updates):
    values = dict(
        user_id="user-1",
        source_event_id="event-1",
        insight_type="recovery",
        safety_action=action,
        safety_reason="Recovery differs from the supplied baseline",
        evidence=[evidence()],
    )
    values.update(updates)
    return InsightCreateRequest(**values)


class InsightServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = InsightService()

    def test_every_action_has_expected_severity(self):
        expected = {
            SafetyAction.NORMAL: InsightSeverity.INFORMATIONAL,
            SafetyAction.OBSERVE: InsightSeverity.LOW,
            SafetyAction.RE_MEASURE: InsightSeverity.MODERATE,
            SafetyAction.SELF_CARE: InsightSeverity.MODERATE,
            SafetyAction.CAREGIVER_ALERT: InsightSeverity.HIGH,
            SafetyAction.EMERGENCY_ESCALATION: InsightSeverity.CRITICAL,
        }
        for index, (action, severity) in enumerate(expected.items()):
            with self.subTest(action=action):
                record = self.service.create(
                    request(action=action, source_event_id=f"event-{index}")
                )
                self.assertEqual(record.severity, severity)
                self.assertEqual(record.safety_action, action)

    def test_summary_uses_only_supplied_evidence(self):
        record = self.service.create(request())
        self.assertIn("sleep", record.summary)
        self.assertIn("5.5 hours", record.summary)
        self.assertNotIn("heart_rate", record.summary)

    def test_disclaimer_is_always_present(self):
        self.assertIn("not a medical diagnosis", self.service.create(request()).disclaimer)

    def test_low_confidence_and_quality_create_limitations(self):
        record = self.service.create(request(evidence=[evidence(0.4, 0.3)]))
        self.assertEqual(len(record.limitations), 2)

    def test_creation_is_user_event_idempotent(self):
        first = self.service.create(request())
        second = self.service.create(request())
        self.assertEqual(first.insight_id, second.insight_id)

    def test_idempotency_is_user_scoped(self):
        first = self.service.create(request(user_id="u1"))
        second = self.service.create(request(user_id="u2"))
        self.assertNotEqual(first.insight_id, second.insight_id)

    def test_view_then_archive(self):
        record = self.service.create(request())
        record = self.service.update_status(record.insight_id, InsightStatus.VIEWED)
        record = self.service.update_status(record.insight_id, InsightStatus.ARCHIVED)
        self.assertEqual(record.status, InsightStatus.ARCHIVED)

    def test_archived_cannot_return_to_viewed(self):
        record = self.service.create(request())
        record = self.service.update_status(record.insight_id, InsightStatus.ARCHIVED)
        with self.assertRaises(InvalidInsightTransitionError):
            self.service.update_status(record.insight_id, InsightStatus.VIEWED)

    def test_list_is_user_scoped(self):
        self.service.create(request(user_id="u1"))
        self.service.create(request(user_id="u2"))
        self.assertEqual(self.service.list_insights("u1").count, 1)

    def test_evidence_is_stored_as_immutable_tuple(self):
        record = self.service.create(request())
        self.assertIsInstance(record.evidence, tuple)


class InsightApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.service = InsightService(InMemoryInsightRepository())
        self.app.dependency_overrides[get_insight_service] = lambda: self.service
        self.client = TestClient(self.app)

    def payload(self):
        return {
            "user_id": "api-user",
            "source_event_id": "api-event",
            "insight_type": "recovery",
            "safety_action": "self_care",
            "safety_reason": "Recovery differs from baseline",
            "evidence": [{
                "metric": "sleep",
                "current_value": 5.5,
                "baseline_value": 7.2,
                "unit": "hours",
                "direction": "below baseline",
                "confidence": 0.9,
                "signal_quality": 0.9,
            }],
        }

    def test_create_get_list_view_and_archive(self):
        created = self.client.post("/api/v1/member3/insights", json=self.payload())
        self.assertEqual(created.status_code, 200)
        insight_id = created.json()["insight_id"]
        self.assertEqual(self.client.get(f"/api/v1/member3/insights/{insight_id}").status_code, 200)
        listed = self.client.get("/api/v1/member3/insights", params={"user_id": "api-user"})
        self.assertEqual(listed.json()["count"], 1)
        viewed = self.client.patch(
            f"/api/v1/member3/insights/{insight_id}/status", json={"status": "viewed"}
        )
        self.assertEqual(viewed.json()["status"], "viewed")
        archived = self.client.patch(
            f"/api/v1/member3/insights/{insight_id}/status", json={"status": "archived"}
        )
        self.assertEqual(archived.json()["status"], "archived")

    def test_missing_insight_returns_404(self):
        self.assertEqual(self.client.get("/api/v1/member3/insights/missing").status_code, 404)

    def test_invalid_evidence_returns_422(self):
        payload = self.payload()
        payload["evidence"][0]["confidence"] = 1.1
        self.assertEqual(self.client.post("/api/v1/member3/insights", json=payload).status_code, 422)


if __name__ == "__main__":
    unittest.main()
