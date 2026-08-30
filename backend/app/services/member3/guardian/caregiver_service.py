"""Two-party caregiver consent without contact details or external delivery."""

from datetime import datetime, timezone
from threading import RLock
from app.schemas.member3.caregivers import (
    CaregiverDecision, CaregiverDecisionRequest, CaregiverLink,
    CaregiverLinkCreate, CaregiverLinkStatus, CaregiverListResponse, new_link_id,
)


class CaregiverLinkNotFoundError(LookupError): pass
class CaregiverAuthorizationError(PermissionError): pass
class InvalidCaregiverTransitionError(ValueError): pass


class CaregiverService:
    def __init__(self) -> None:
        self._links: dict[str, CaregiverLink] = {}
        self._pair_index: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def create(self, request: CaregiverLinkCreate) -> CaregiverLink:
        if request.user_id == request.caregiver_user_ref:
            raise ValueError("A user cannot be their own caregiver")
        key = (request.user_id, request.caregiver_user_ref)
        with self._lock:
            existing_id = self._pair_index.get(key)
            if existing_id and self._links[existing_id].status in {
                CaregiverLinkStatus.PENDING, CaregiverLinkStatus.ACTIVE
            }:
                return self._links[existing_id]
            now = datetime.now(timezone.utc)
            link = CaregiverLink(
                link_id=new_link_id(), user_id=request.user_id,
                caregiver_user_ref=request.caregiver_user_ref,
                relationship_label=request.relationship_label,
                status=CaregiverLinkStatus.PENDING, created_at=now, updated_at=now,
            )
            self._links[link.link_id] = link
            self._pair_index[key] = link.link_id
            return link

    def decide(self, link_id: str, request: CaregiverDecisionRequest) -> CaregiverLink:
        with self._lock:
            link = self._links.get(link_id)
            if link is None: raise CaregiverLinkNotFoundError("Caregiver link not found")
            if request.decision in {CaregiverDecision.ACCEPT, CaregiverDecision.DECLINE}:
                if request.actor_user_ref != link.caregiver_user_ref:
                    raise CaregiverAuthorizationError("Only the invited caregiver may accept or decline")
                if link.status != CaregiverLinkStatus.PENDING:
                    raise InvalidCaregiverTransitionError("Only pending links may be accepted or declined")
                status = CaregiverLinkStatus.ACTIVE if request.decision == CaregiverDecision.ACCEPT else CaregiverLinkStatus.DECLINED
            else:
                if request.actor_user_ref not in {link.user_id, link.caregiver_user_ref}:
                    raise CaregiverAuthorizationError("Only a linked party may revoke consent")
                if link.status != CaregiverLinkStatus.ACTIVE:
                    raise InvalidCaregiverTransitionError("Only active links may be revoked")
                status = CaregiverLinkStatus.REVOKED
            updated = link.model_copy(update={"status": status, "updated_at": datetime.now(timezone.utc)})
            self._links[link_id] = updated
            return updated

    def list_for_user(self, user_id: str) -> CaregiverListResponse:
        user_id = " ".join(user_id.split())
        with self._lock:
            links = [x for x in self._links.values() if x.user_id == user_id]
        links.sort(key=lambda x: (x.created_at, x.link_id), reverse=True)
        return CaregiverListResponse(user_id=user_id, links=links, count=len(links))

    def is_active(self, user_id: str, caregiver_ref: str) -> bool:
        with self._lock:
            link_id = self._pair_index.get((user_id, caregiver_ref))
            return bool(link_id and self._links[link_id].status == CaregiverLinkStatus.ACTIVE)
