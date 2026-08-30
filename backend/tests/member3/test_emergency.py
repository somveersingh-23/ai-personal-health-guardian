"""Offline tests for the Member 3 emergency-workflow prototype."""

from datetime import datetime, timezone
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.member3.emergency import get_emergency_service, router
from app.schemas.member3.emergency import (
    EmergencyCommand,
    EmergencyCommandRequest,
    EmergencyStartRequest,
    EmergencyState,
)
from app.services.member3.guardian.emergency_service import (
    EmergencyWorkflowService,
    InMemoryEmergencyRepository,
    InvalidEmergencyTransitionError,
    MissingCaregiverContactError,
)
from ml.safety import SafetyAction


def start_request(**updates):
    values = dict(
        user_id="user-1",
        alert_id="alert-1",
        safety_action=SafetyAction.EMERGENCY_ESCALATION,
        safety_reason="Confirmed severe symptoms",
        evidence=["User confirmed severe symptoms"],
        caregiver_contact_id="caregiver-1",
    )
    values.update(updates)
    return EmergencyStartRequest(**values)


def command(value, actor="user-1", note=None):
    return EmergencyCommandRequest(command=value, actor_id=actor, note=note)


class EmergencySchemaTests(unittest.TestCase):
    def test_non_emergency_action_is_rejected(self):
        with self.assertRaises(ValidationError):
            start_request(safety_action=SafetyAction.CAREGIVER_ALERT)

    def test_strings_and_evidence_are_normalised(self):
        request = start_request(
            user_id=" user-1 ", evidence=[" Severe symptom ", "severe SYMPTOM"]
        )
        self.assertEqual(request.user_id, "user-1")
        self.assertEqual(request.evidence, ["Severe symptom"])

    def test_blank_contact_is_rejected(self):
        with self.assertRaises(ValidationError):
            start_request(caregiver_contact_id="   ")


class EmergencyServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = EmergencyWorkflowService()

    def test_start_is_idempotent_per_user_and_alert(self):
        first = self.service.start(start_request())
        second = self.service.start(start_request())
        self.assertEqual(first.workflow_id, second.workflow_id)

    def test_start_includes_immediate_instruction_and_no_external_claim(self):
        record = self.service.start(start_request())
        self.assertIn("call your local emergency services now", record.urgent_instruction)
        self.assertFalse(record.external_action_performed)
        self.assertEqual(record.state, EmergencyState.AWAITING_CONFIRMATION)

    def test_confirmation_is_audited(self):
        record = self.service.start(start_request())
        updated = self.service.command(record.workflow_id, command(EmergencyCommand.CONFIRM))
        self.assertEqual(updated.state, EmergencyState.CONFIRMED)
        self.assertEqual([event.sequence for event in updated.audit_events], [1, 2])

    def test_stored_evidence_and_audit_trail_are_immutable_tuples(self):
        record = self.service.start(start_request())
        self.assertIsInstance(record.evidence, tuple)
        self.assertIsInstance(record.audit_events, tuple)
        with self.assertRaises(TypeError):
            record.audit_events[0] = record.audit_events[0]

    def test_full_caregiver_then_contact_then_resolve_flow(self):
        record = self.service.start(start_request())
        record = self.service.command(record.workflow_id, command(EmergencyCommand.CONFIRM))
        record = self.service.command(
            record.workflow_id, command(EmergencyCommand.RECORD_CAREGIVER_NOTIFICATION)
        )
        self.assertEqual(record.state, EmergencyState.CAREGIVER_NOTIFICATION_RECORDED)
        record = self.service.command(
            record.workflow_id, command(EmergencyCommand.REQUEST_EMERGENCY_CONTACT)
        )
        self.assertEqual(record.state, EmergencyState.EMERGENCY_CONTACT_REQUESTED)
        self.assertFalse(record.external_action_performed)
        record = self.service.command(record.workflow_id, command(EmergencyCommand.RESOLVE))
        self.assertEqual(record.state, EmergencyState.RESOLVED)

    def test_caregiver_record_requires_configured_contact(self):
        record = self.service.start(start_request(caregiver_contact_id=None))
        record = self.service.command(record.workflow_id, command(EmergencyCommand.CONFIRM))
        with self.assertRaises(MissingCaregiverContactError):
            self.service.command(
                record.workflow_id,
                command(EmergencyCommand.RECORD_CAREGIVER_NOTIFICATION),
            )

    def test_requesting_contact_before_confirmation_is_rejected(self):
        record = self.service.start(start_request())
        with self.assertRaises(InvalidEmergencyTransitionError):
            self.service.command(
                record.workflow_id, command(EmergencyCommand.REQUEST_EMERGENCY_CONTACT)
            )

    def test_cancel_does_not_claim_user_is_safe(self):
        record = self.service.start(start_request())
        record = self.service.command(
            record.workflow_id,
            command(EmergencyCommand.CANCEL, note="User cancelled workflow"),
        )
        self.assertEqual(record.state, EmergencyState.CANCELLED)
        self.assertIn("Do not wait for this prototype", record.urgent_instruction)

    def test_terminal_state_rejects_further_commands(self):
        record = self.service.start(start_request())
        record = self.service.command(record.workflow_id, command(EmergencyCommand.CANCEL))
        with self.assertRaises(InvalidEmergencyTransitionError):
            self.service.command(record.workflow_id, command(EmergencyCommand.CONFIRM))

    def test_user_scoped_alert_idempotency(self):
        first = self.service.start(start_request(user_id="u1", alert_id="shared"))
        second = self.service.start(start_request(user_id="u2", alert_id="shared"))
        self.assertNotEqual(first.workflow_id, second.workflow_id)

    def test_list_is_user_scoped(self):
        self.service.start(start_request(user_id="u1", alert_id="a1"))
        self.service.start(start_request(user_id="u2", alert_id="a2"))
        result = self.service.list_workflows("u1")
        self.assertEqual(result.count, 1)
        self.assertEqual(result.workflows[0].user_id, "u1")


class EmergencyApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.service = EmergencyWorkflowService(InMemoryEmergencyRepository())
        self.app.dependency_overrides[get_emergency_service] = lambda: self.service
        self.client = TestClient(self.app)

    def payload(self):
        return {
            "user_id": "api-user",
            "alert_id": "api-alert",
            "safety_action": "emergency_escalation",
            "safety_reason": "Confirmed severe symptoms",
            "evidence": ["Confirmed severe symptoms"],
            "caregiver_contact_id": "caregiver-1",
        }

    def test_start_get_list_and_confirm(self):
        started = self.client.post("/api/v1/member3/emergency/workflows", json=self.payload())
        self.assertEqual(started.status_code, 200)
        workflow_id = started.json()["workflow_id"]
        fetched = self.client.get(f"/api/v1/member3/emergency/workflows/{workflow_id}")
        self.assertEqual(fetched.status_code, 200)
        listed = self.client.get(
            "/api/v1/member3/emergency/workflows", params={"user_id": "api-user"}
        )
        self.assertEqual(listed.json()["count"], 1)
        confirmed = self.client.post(
            f"/api/v1/member3/emergency/workflows/{workflow_id}/commands",
            json={"command": "confirm", "actor_id": "api-user"},
        )
        self.assertEqual(confirmed.json()["state"], "confirmed")

    def test_invalid_action_returns_422(self):
        payload = self.payload()
        payload["safety_action"] = "observe"
        self.assertEqual(
            self.client.post("/api/v1/member3/emergency/workflows", json=payload).status_code,
            422,
        )

    def test_missing_workflow_returns_404(self):
        response = self.client.get("/api/v1/member3/emergency/workflows/missing")
        self.assertEqual(response.status_code, 404)

    def test_invalid_transition_returns_409(self):
        started = self.client.post("/api/v1/member3/emergency/workflows", json=self.payload())
        workflow_id = started.json()["workflow_id"]
        response = self.client.post(
            f"/api/v1/member3/emergency/workflows/{workflow_id}/commands",
            json={"command": "request_emergency_contact", "actor_id": "api-user"},
        )
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
