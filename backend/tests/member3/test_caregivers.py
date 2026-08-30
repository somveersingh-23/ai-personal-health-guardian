import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.member3.caregivers import get_caregiver_service, router
from app.schemas.member3.caregivers import CaregiverDecision, CaregiverDecisionRequest, CaregiverLinkCreate, CaregiverLinkStatus
from app.services.member3.guardian.caregiver_service import CaregiverAuthorizationError, CaregiverService, InvalidCaregiverTransitionError


class CaregiverTests(unittest.TestCase):
    def setUp(self): self.service = CaregiverService()
    def create(self): return self.service.create(CaregiverLinkCreate(user_id="u1", caregiver_user_ref="c1", relationship_label="Family"))
    def test_two_party_accept_and_revoke(self):
        link = self.create()
        link = self.service.decide(link.link_id, CaregiverDecisionRequest(decision=CaregiverDecision.ACCEPT, actor_user_ref="c1"))
        self.assertTrue(self.service.is_active("u1", "c1"))
        link = self.service.decide(link.link_id, CaregiverDecisionRequest(decision=CaregiverDecision.REVOKE, actor_user_ref="u1"))
        self.assertEqual(link.status, CaregiverLinkStatus.REVOKED)
    def test_wrong_user_cannot_accept(self):
        with self.assertRaises(CaregiverAuthorizationError):
            self.service.decide(self.create().link_id, CaregiverDecisionRequest(decision="accept", actor_user_ref="x"))
    def test_pending_cannot_revoke(self):
        with self.assertRaises(InvalidCaregiverTransitionError):
            self.service.decide(self.create().link_id, CaregiverDecisionRequest(decision="revoke", actor_user_ref="u1"))
    def test_self_link_rejected(self):
        with self.assertRaises(ValueError): self.service.create(CaregiverLinkCreate(user_id="u", caregiver_user_ref="u", relationship_label="Self"))
    def test_idempotent_pending_link(self): self.assertEqual(self.create().link_id, self.create().link_id)
    def test_list_user_scoped(self):
        self.create(); self.service.create(CaregiverLinkCreate(user_id="u2", caregiver_user_ref="c2", relationship_label="Friend"))
        self.assertEqual(self.service.list_for_user("u1").count, 1)


class CaregiverApiTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI(); app.include_router(router); service=CaregiverService(); app.dependency_overrides[get_caregiver_service]=lambda:service; self.client=TestClient(app)
    def test_create_accept_list(self):
        created=self.client.post("/api/v1/member3/caregivers",json={"user_id":"u1","caregiver_user_ref":"c1","relationship_label":"Family"})
        lid=created.json()["link_id"]
        accepted=self.client.post(f"/api/v1/member3/caregivers/{lid}/decisions",json={"decision":"accept","actor_user_ref":"c1"})
        self.assertEqual(accepted.json()["status"],"active")
        self.assertEqual(self.client.get("/api/v1/member3/caregivers",params={"user_id":"u1"}).json()["count"],1)
    def test_unauthorized_returns_403(self):
        lid=self.client.post("/api/v1/member3/caregivers",json={"user_id":"u1","caregiver_user_ref":"c1","relationship_label":"Family"}).json()["link_id"]
        self.assertEqual(self.client.post(f"/api/v1/member3/caregivers/{lid}/decisions",json={"decision":"accept","actor_user_ref":"x"}).status_code,403)

if __name__ == "__main__": unittest.main()
