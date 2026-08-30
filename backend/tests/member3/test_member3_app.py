"""Cross-router tests for the standalone Member 3 integration harness."""

import unittest

from fastapi.testclient import TestClient

from app.api.member3.app import create_member3_app


def guardian_payload(*, severe=False):
    return {
        "user_id": "integration-user",
        "event_id": "event-emergency" if severe else "event-self-care",
        "insight_type": "recovery",
        "deviation_score": 0 if severe else 1.8,
        "confidence": 0.1 if severe else 0.9,
        "signal_quality": 0.1 if severe else 0.9,
        "evidence": [{
            "metric": "sleep",
            "current_value": 5.5,
            "baseline_value": 7.2,
            "unit": "hours",
            "direction": "below baseline",
            "confidence": 0.9,
            "signal_quality": 0.9,
        }],
        "critical_flags": [],
        "user_confirmed_severe_symptoms": severe,
        "occurred_at": "2026-08-30T12:00:00Z",
        "notification_channels": ["in_app"],
        "consented_channels": ["in_app"],
        "channel_targets": {},
        "caregiver_contact_id": "caregiver-1" if severe else None,
    }


class Member3AppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_member3_app()
        self.client = TestClient(self.app)

    def test_health_endpoint_discloses_development_limitations(self):
        response = self.client.get("/api/v1/member3/health")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["external_connectors_enabled"])
        self.assertEqual(response.json()["persistence"], "in_memory")

    def test_expected_member3_routes_are_registered(self):
        # FastAPI 0.141 lazily represents included routers in ``app.routes``;
        # the generated OpenAPI contract is the stable public route inventory.
        paths = set(self.app.openapi()["paths"])
        expected = {
            "/api/v1/member3/assistant/explain",
            "/api/v1/member3/rag/retrieve",
            "/api/v1/member3/insights",
            "/api/v1/member3/alerts/evaluate",
            "/api/v1/member3/notifications",
            "/api/v1/member3/emergency/workflows",
            "/api/v1/member3/guardian/process",
            "/api/v1/member3/health",
            "/api/v1/member3/safety/evaluate",
        }
        self.assertTrue(expected.issubset(paths))

    def test_guardian_self_care_outputs_are_visible_through_other_apis(self):
        processed = self.client.post(
            "/api/v1/member3/guardian/process", json=guardian_payload()
        )
        self.assertEqual(processed.status_code, 200)
        body = processed.json()
        self.assertEqual(body["safety_action"], "self_care")

        insights = self.client.get(
            "/api/v1/member3/insights", params={"user_id": "integration-user"}
        ).json()
        alerts = self.client.get(
            "/api/v1/member3/alerts", params={"user_id": "integration-user"}
        ).json()
        notifications = self.client.get(
            "/api/v1/member3/notifications",
            params={"user_id": "integration-user"},
        ).json()
        self.assertEqual(insights["count"], 1)
        self.assertEqual(alerts["count"], 1)
        self.assertEqual(notifications["count"], 1)

    def test_emergency_pipeline_is_visible_through_emergency_api(self):
        processed = self.client.post(
            "/api/v1/member3/guardian/process", json=guardian_payload(severe=True)
        )
        self.assertEqual(processed.status_code, 200)
        body = processed.json()
        self.assertEqual(body["safety_action"], "emergency_escalation")
        self.assertFalse(body["emergency_workflow"]["external_action_performed"])
        workflows = self.client.get(
            "/api/v1/member3/emergency/workflows",
            params={"user_id": "integration-user"},
        ).json()
        self.assertEqual(workflows["count"], 1)

    def test_rag_default_dependency_works_in_integrated_app(self):
        response = self.client.post(
            "/api/v1/member3/rag/retrieve",
            json={"question": "Why can sleep affect recovery?", "top_k": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["result_count"], 0)

    def test_assistant_default_dependency_works_in_integrated_app(self):
        response = self.client.post(
            "/api/v1/member3/assistant/explain",
            json={
                "user_id": "integration-user",
                "question": "Why is recovery lower?",
                "evidence": [{
                    "metric": "sleep",
                    "current_value": 5.5,
                    "baseline_value": 7.2,
                    "unit": "hours",
                    "direction": "below baseline",
                    "confidence": 0.9,
                    "signal_quality": 0.9,
                }],
                "safety_action": "self_care",
                "safety_reason": "Recovery differs from baseline",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["safety_action"], "self_care")
        self.assertIn("not a medical diagnosis", response.json()["disclaimer"])

    def test_openapi_contains_only_member3_business_paths(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        business_paths = [path for path in paths if path.startswith("/api/")]
        self.assertTrue(business_paths)
        self.assertTrue(all(path.startswith("/api/v1/member3/") for path in business_paths))

    def test_separate_app_instances_do_not_share_state(self):
        self.client.post("/api/v1/member3/guardian/process", json=guardian_payload())
        other = TestClient(create_member3_app())
        result = other.get(
            "/api/v1/member3/insights", params={"user_id": "integration-user"}
        ).json()
        self.assertEqual(result["count"], 0)


if __name__ == "__main__":
    unittest.main()
