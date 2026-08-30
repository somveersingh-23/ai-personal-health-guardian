"""API-contract tests for deterministic safety evaluation."""

import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.member3.safety import get_safety_service, router
from app.schemas.member3.safety import SafetyEvaluationRequest
from app.services.member3.guardian.safety_service import SafetyEvaluationService
from ml.safety import SafetyAction


class SafetyEvaluationServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = SafetyEvaluationService()

    def evaluate(self, score, confidence=.9, quality=.9, **updates):
        return self.service.evaluate(SafetyEvaluationRequest(
            deviation_score=score, confidence=confidence, signal_quality=quality, **updates
        ))

    def test_all_standard_action_paths(self):
        self.assertEqual(self.evaluate(0).action, SafetyAction.NORMAL)
        self.assertEqual(self.evaluate(.5).action, SafetyAction.OBSERVE)
        self.assertEqual(self.evaluate(1.5).action, SafetyAction.SELF_CARE)
        self.assertEqual(self.evaluate(2.5).action, SafetyAction.CAREGIVER_ALERT)
        self.assertEqual(self.evaluate(3, quality=.2).action, SafetyAction.RE_MEASURE)

    def test_critical_flag_and_severe_symptom_paths(self):
        self.assertEqual(
            self.evaluate(0, critical_flags=["validated flag"]).action,
            SafetyAction.EMERGENCY_ESCALATION,
        )
        result = self.evaluate(
            0, confidence=.1, quality=.1, user_confirmed_severe_symptoms=True
        )
        self.assertEqual(result.action, SafetyAction.EMERGENCY_ESCALATION)
        self.assertTrue(result.requires_human_confirmation)

    def test_evidence_and_flags_are_cleaned(self):
        result = self.evaluate(
            3, confidence=.8, evidence=[" sleep low ", "SLEEP LOW"],
            critical_flags=[" flag "],
        )
        self.assertEqual(result.evidence, ("sleep low", "flag"))

    def test_disclaimer_always_present(self):
        self.assertIn("not a medical diagnosis", self.evaluate(0).disclaimer)


class SafetyApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_safety_service] = lambda: SafetyEvaluationService()
        self.client = TestClient(app)

    def test_evaluate_endpoint(self):
        response = self.client.post("/api/v1/member3/safety/evaluate", json={
            "deviation_score": 1.5, "confidence": .9, "signal_quality": .9,
            "evidence": ["sleep below baseline"]
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["action"], "self_care")

    def test_invalid_numbers_return_422(self):
        for field, value in (("deviation_score", -1), ("confidence", 1.1), ("signal_quality", -.1)):
            payload = {"deviation_score": 1, "confidence": .9, "signal_quality": .9}
            payload[field] = value
            with self.subTest(field=field):
                self.assertEqual(
                    self.client.post("/api/v1/member3/safety/evaluate", json=payload).status_code,
                    422,
                )


if __name__ == "__main__":
    unittest.main()
