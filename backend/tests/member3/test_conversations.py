"""Conversation lifecycle, safety, idempotency, and privacy tests."""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.member3.conversations import get_conversation_service, router
from app.schemas.member3.assistant import EvidenceItem
from app.schemas.member3.conversations import ConversationMessageRequest
from app.services.member3.guardian.conversation_service import (
    ConversationNotFoundError,
    ConversationOwnershipError,
    ConversationService,
    InMemoryConversationRepository,
)
from ml.safety import SafetyAction


def message(message_id="m1", conversation_id=None, user_id="u1"):
    return ConversationMessageRequest(
        user_id=user_id,
        message_id=message_id,
        conversation_id=conversation_id,
        question="Why is recovery lower?",
        safety_action=SafetyAction.SELF_CARE,
        safety_reason="Recovery differs from baseline",
        evidence=[EvidenceItem(metric="sleep", current_value=5.5, baseline_value=7.2, unit="hours", direction="below baseline", confidence=.9, signal_quality=.9)],
    )


class ConversationServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = ConversationService()

    def test_new_and_followup_turns(self):
        first = self.service.send(message())
        second = self.service.send(message("m2", first.conversation_id))
        self.assertEqual(len(second.turns), 2)
        self.assertEqual(second.turns[0].evidence_metrics, ("sleep",))

    def test_message_is_idempotent(self):
        self.assertEqual(self.service.send(message()), self.service.send(message()))

    def test_history_is_user_scoped(self):
        self.service.send(message(user_id="u1"))
        self.service.send(message(message_id="m2", user_id="u2"))
        self.assertEqual(self.service.list_conversations("u1").count, 1)

    def test_cross_user_access_is_rejected(self):
        record = self.service.send(message(user_id="u1"))
        with self.assertRaises(ConversationOwnershipError):
            self.service.get(record.conversation_id, "u2")

    def test_delete_removes_conversation_and_message_index(self):
        record = self.service.send(message())
        self.assertTrue(self.service.delete(record.conversation_id, "u1").deleted)
        with self.assertRaises(ConversationNotFoundError):
            self.service.get(record.conversation_id, "u1")
        recreated = self.service.send(message())
        self.assertNotEqual(record.conversation_id, recreated.conversation_id)

    def test_turns_are_immutable_tuples(self):
        self.assertIsInstance(self.service.send(message()).turns, tuple)

    def test_disclaimer_and_safety_action_preserved(self):
        turn = self.service.send(message()).turns[0]
        self.assertEqual(turn.safety_action, SafetyAction.SELF_CARE)
        self.assertIn("not a medical diagnosis", turn.disclaimer)


class ConversationApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.service = ConversationService(repository=InMemoryConversationRepository())
        app.dependency_overrides[get_conversation_service] = lambda: self.service
        self.client = TestClient(app)

    def payload(self, conversation_id=None):
        data = message(conversation_id=conversation_id).model_dump(mode="json")
        return data

    def test_send_get_list_delete(self):
        created = self.client.post("/api/v1/member3/conversations/messages", json=self.payload())
        self.assertEqual(created.status_code, 200)
        cid = created.json()["conversation_id"]
        self.assertEqual(self.client.get(f"/api/v1/member3/conversations/{cid}", params={"user_id":"u1"}).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/member3/conversations", params={"user_id":"u1"}).json()["count"], 1)
        self.assertTrue(self.client.delete(f"/api/v1/member3/conversations/{cid}", params={"user_id":"u1"}).json()["deleted"])

    def test_cross_user_returns_403(self):
        created = self.client.post("/api/v1/member3/conversations/messages", json=self.payload())
        cid = created.json()["conversation_id"]
        self.assertEqual(self.client.get(f"/api/v1/member3/conversations/{cid}", params={"user_id":"u2"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
