"""Cross-store Member 3 export and deletion tests."""

import unittest
from fastapi.testclient import TestClient
from app.api.member3.app import create_member3_app


class DataControlTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_member3_app())

    def payload(self, user="privacy-user"):
        return {
            "user_id": user, "event_id": "privacy-event", "insight_type": "recovery",
            "deviation_score": 1.8, "confidence": .9, "signal_quality": .9,
            "evidence": [{"metric":"sleep","current_value":5.5,"baseline_value":7.2,
                          "unit":"hours","direction":"below baseline","confidence":.9,"signal_quality":.9}],
            "occurred_at":"2026-08-30T12:00:00Z", "notification_channels":["in_app"],
            "consented_channels":["in_app"], "channel_targets": {}
        }

    def test_export_contains_cross_store_user_data(self):
        self.client.post("/api/v1/member3/guardian/process", json=self.payload())
        export = self.client.get("/api/v1/member3/data/export", params={"user_id":"privacy-user"})
        self.assertEqual(export.status_code, 200)
        body = export.json()
        self.assertEqual(len(body["insights"]), 1)
        self.assertEqual(len(body["alerts"]), 1)
        self.assertEqual(len(body["notifications"]), 1)
        self.assertEqual(len(body["guardian_decisions"]), 1)
        self.assertEqual(
            body["guardian_decisions"][0]["policy_version"],
            "member3-safety-rules-v1",
        )

    def test_purge_removes_all_user_data_and_cache(self):
        self.client.post("/api/v1/member3/guardian/process", json=self.payload())
        purged = self.client.delete("/api/v1/member3/data", params={"user_id":"privacy-user"})
        self.assertGreaterEqual(purged.json()["total_deleted"], 4)
        export = self.client.get("/api/v1/member3/data/export", params={"user_id":"privacy-user"}).json()
        self.assertTrue(all(not export[key] for key in (
            "insights","alerts","notifications","emergency_workflows","conversations","guardian_decisions")))
        # Cache deletion means the same event can be processed as new again.
        self.assertEqual(self.client.post("/api/v1/member3/guardian/process", json=self.payload()).status_code, 200)

    def test_purge_is_user_scoped(self):
        self.client.post("/api/v1/member3/guardian/process", json=self.payload("u1"))
        other = self.payload("u2")
        other["event_id"] = "other-event"
        self.client.post("/api/v1/member3/guardian/process", json=other)
        self.client.delete("/api/v1/member3/data", params={"user_id":"u1"})
        export = self.client.get("/api/v1/member3/data/export", params={"user_id":"u2"}).json()
        self.assertEqual(len(export["insights"]), 1)


if __name__ == "__main__":
    unittest.main()
