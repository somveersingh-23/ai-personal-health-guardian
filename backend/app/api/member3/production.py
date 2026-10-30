from __future__ import annotations

import os

from fastapi import FastAPI

from app.api.member3.alerts import get_alert_service
from app.api.member3.app import Member3ServiceContainer
from app.api.member3.assistant import get_explanation_service
from app.api.member3.caregivers import get_caregiver_service
from app.api.member3.conversations import get_conversation_service
from app.api.member3.data_controls import get_data_control_service
from app.api.member3.emergency import get_emergency_service
from app.api.member3.guardian import get_guardian_service
from app.api.member3.insights import get_insight_service
from app.api.member3.notifications import get_notification_service
from app.api.member3.rag import get_retrieval_service
from app.api.member3.registration import register_member3_routers
from app.api.member3.safety import get_safety_service
from app.services.member3.persistence.container import build_persistent_container, create_member3_engine


def create_production_member3_app(*, database_url: str | None = None, create_schema: bool = False) -> FastAPI:
    url = database_url or os.environ.get("MEMBER3_DATABASE_URL")
    if not url:
        raise RuntimeError("MEMBER3_DATABASE_URL must be configured")
    services = build_persistent_container(create_member3_engine(url), create_schema=create_schema)
    app = FastAPI(title="AI Personal Health Guardian - Member 3 API", version="1.0.0")
    register_member3_routers(app, require_auth=True)
    _override_services(app, services)
    app.state.member3_services = services
    return app


def _override_services(app: FastAPI, services: Member3ServiceContainer) -> None:
    for dependency, service in (
        (get_explanation_service, services.explanation), (get_retrieval_service, services.retrieval),
        (get_insight_service, services.insights), (get_alert_service, services.alerts),
        (get_notification_service, services.notifications), (get_emergency_service, services.emergency),
        (get_conversation_service, services.conversations), (get_data_control_service, services.data_controls),
        (get_safety_service, services.safety), (get_caregiver_service, services.caregivers),
        (get_guardian_service, services.guardian),
    ):
        app.dependency_overrides[dependency] = _provider(service)


def _provider(service):
    def provide():
        return service
    return provide
