"""Single integration point for registering Member 3 routers."""

from fastapi import Depends, FastAPI

from app.api.member3.alerts import router as alerts_router
from app.api.member3.assistant import router as assistant_router
from app.api.member3.caregivers import router as caregivers_router
from app.api.member3.conversations import router as conversations_router
from app.api.member3.data_controls import router as data_controls_router
from app.api.member3.emergency import router as emergency_router
from app.api.member3.guardian import router as guardian_router
from app.api.member3.insights import router as insights_router
from app.api.member3.notifications import router as notifications_router
from app.api.member3.rag import router as rag_router
from app.api.member3.safety import router as safety_router
from app.core.member3.security import require_member3_identity

MEMBER3_ROUTERS = (
    assistant_router, rag_router, insights_router, alerts_router,
    notifications_router, emergency_router, conversations_router,
    data_controls_router, safety_router, caregivers_router, guardian_router,
)


def register_member3_routers(app: FastAPI, *, require_auth: bool = True) -> None:
    dependencies = [Depends(require_member3_identity)] if require_auth else None
    for router in MEMBER3_ROUTERS:
        app.include_router(router, dependencies=dependencies)
