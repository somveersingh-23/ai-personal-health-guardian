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


class InMemoryCaregiverRepository:
    def __init__(self) -> None:
        self._links: dict[str, CaregiverLink] = {}
        self._pair_index: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def save(self, link: CaregiverLink) -> None:
        with self._lock:
            self._links[link.link_id] = link
            self._pair_index[(link.user_id, link.caregiver_user_ref)] = link.link_id

    def get(self, link_id: str) -> CaregiverLink | None:
        with self._lock:
            return self._links.get(link_id)

    def get_by_pair(self, user_id: str, caregiver_user_ref: str) -> CaregiverLink | None:
        with self._lock:
            link_id = self._pair_index.get((user_id, caregiver_user_ref))
            return self._links.get(link_id) if link_id else None

    def list_for_user(self, user_id: str) -> list[CaregiverLink]:
        with self._lock:
            return [x for x in self._links.values() if x.user_id == user_id]

    def delete_for_user(self, user_id: str) -> int:
        with self._lock:
            to_remove = [k for k, v in self._links.items() if v.user_id == user_id]
            for k in to_remove:
                link = self._links.pop(k)
                self._pair_index.pop((link.user_id, link.caregiver_user_ref), None)
            return len(to_remove)


class CaregiverService:
    def __init__(self, repository: InMemoryCaregiverRepository | None = None) -> None:
        self._repository = repository or InMemoryCaregiverRepository()
        self._lock = RLock()

    def create(self, request: CaregiverLinkCreate) -> CaregiverLink:
        if request.user_id == request.caregiver_user_ref:
            raise ValueError("A user cannot be their own caregiver")
        with self._lock:
            existing = self._repository.get_by_pair(request.user_id, request.caregiver_user_ref)
            if existing and existing.status in {CaregiverLinkStatus.PENDING, CaregiverLinkStatus.ACTIVE}:
                return existing
            now = datetime.now(timezone.utc)
            link = CaregiverLink(
                link_id=new_link_id(), user_id=request.user_id,
                caregiver_user_ref=request.caregiver_user_ref,
                relationship_label=request.relationship_label,
                status=CaregiverLinkStatus.PENDING, created_at=now, updated_at=now,
            )
            self._repository.save(link)
            return link

    def decide(self, link_id: str, request: CaregiverDecisionRequest) -> CaregiverLink:
        with self._lock:
            link = self._repository.get(link_id)
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
            self._repository.save(updated)
            return updated

    def list_for_user(self, user_id: str) -> CaregiverListResponse:
        cleaned = " ".join(user_id.split())
        links = self._repository.list_for_user(cleaned)
        links_sorted = sorted(links, key=lambda x: (x.created_at, x.link_id), reverse=True)
        return CaregiverListResponse(user_id=cleaned, links=links_sorted, count=len(links_sorted))

    def is_active(self, user_id: str, caregiver_ref: str) -> bool:
        link = self._repository.get_by_pair(user_id, caregiver_ref)
        return bool(link and link.status == CaregiverLinkStatus.ACTIVE)

    def purge_user(self, user_id: str) -> int:
        return self._repository.delete_for_user(" ".join(user_id.split()))
