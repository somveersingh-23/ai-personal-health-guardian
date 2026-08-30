"""Standalone Member 3 FastAPI integration harness.

This app factory is for development and tests. It does not replace or modify
the team's shared ``app.main`` application.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI

from app.api.member3.alerts import (
    get_alert_service,
    router as alerts_router,
)
from app.api.member3.assistant import (
    get_explanation_service,
    router as assistant_router,
)
from app.api.member3.emergency import (
    get_emergency_service,
    router as emergency_router,
)
from app.api.member3.conversations import (
    get_conversation_service,
    router as conversations_router,
)
from app.api.member3.data_controls import (
    get_data_control_service,
    router as data_controls_router,
)
from app.api.member3.safety import (
    get_safety_service,
    router as safety_router,
)
from app.api.member3.guardian import (
    get_guardian_service,
    router as guardian_router,
)
from app.api.member3.insights import (
    get_insight_service,
    router as insights_router,
)
from app.api.member3.notifications import (
    get_notification_service,
    router as notifications_router,
)
from app.api.member3.rag import (
    get_retrieval_service,
    router as rag_router,
)
from app.services.member3.guardian.alert_service import (
    AlertService,
    InMemoryAlertRepository,
)
from app.services.member3.guardian.emergency_service import (
    EmergencyWorkflowService,
    InMemoryEmergencyRepository,
)
from app.services.member3.guardian.conversation_service import (
    ConversationService,
    InMemoryConversationRepository,
)
from app.services.member3.guardian.data_control_service import DataControlService
from app.services.member3.guardian.safety_service import SafetyEvaluationService
from app.services.member3.guardian.explanation_service import ExplanationService
from app.services.member3.guardian.insight_service import (
    InMemoryInsightRepository,
    InsightService,
)
from app.services.member3.guardian.notification_service import (
    InMemoryNotificationRepository,
    NotificationService,
)
from app.services.member3.guardian.orchestration_service import GuardianOrchestrationService
from app.services.member3.guardian.retrieval_service import RetrievalService


@dataclass(frozen=True)
class Member3ServiceContainer:
    explanation: ExplanationService
    retrieval: RetrievalService
    insights: InsightService
    alerts: AlertService
    notifications: NotificationService
    emergency: EmergencyWorkflowService
    conversations: ConversationService
    data_controls: DataControlService
    safety: SafetyEvaluationService
    guardian: GuardianOrchestrationService


def build_service_container() -> Member3ServiceContainer:
    """Create one isolated set of services shared by all Member 3 routers."""
    insights = InsightService(InMemoryInsightRepository())
    alerts = AlertService(InMemoryAlertRepository())
    notifications = NotificationService(InMemoryNotificationRepository())
    emergency = EmergencyWorkflowService(InMemoryEmergencyRepository())
    explanation = ExplanationService()
    conversations = ConversationService(
        explanation_service=explanation,
        repository=InMemoryConversationRepository(),
    )
    guardian = GuardianOrchestrationService(
        insight_service=insights,
        alert_service=alerts,
        notification_service=notifications,
        emergency_service=emergency,
    )
    data_controls = DataControlService(
        insights=insights, alerts=alerts, notifications=notifications,
        emergency=emergency, conversations=conversations, guardian=guardian,
    )
    return Member3ServiceContainer(
        explanation=explanation,
        retrieval=get_retrieval_service(),
        insights=insights,
        alerts=alerts,
        notifications=notifications,
        emergency=emergency,
        conversations=conversations,
        data_controls=data_controls,
        safety=SafetyEvaluationService(),
        guardian=guardian,
    )


def create_member3_app(
    container: Member3ServiceContainer | None = None,
) -> FastAPI:
    """Return a standalone app containing only Member 3 endpoints."""
    services = container or build_service_container()
    app = FastAPI(
        title="AI Personal Health Guardian - Member 3 Development API",
        description=(
            "Standalone development harness for AI Guardian, safety, insights, "
            "alerts, notifications, emergency workflow, and RAG."
        ),
        version="0.1.0-member3",
    )

    for router in (
        assistant_router,
        rag_router,
        insights_router,
        alerts_router,
        notifications_router,
        emergency_router,
        conversations_router,
        data_controls_router,
        safety_router,
        guardian_router,
    ):
        app.include_router(router)

    app.dependency_overrides[get_explanation_service] = lambda: services.explanation
    app.dependency_overrides[get_retrieval_service] = lambda: services.retrieval
    app.dependency_overrides[get_insight_service] = lambda: services.insights
    app.dependency_overrides[get_alert_service] = lambda: services.alerts
    app.dependency_overrides[get_notification_service] = lambda: services.notifications
    app.dependency_overrides[get_emergency_service] = lambda: services.emergency
    app.dependency_overrides[get_conversation_service] = lambda: services.conversations
    app.dependency_overrides[get_data_control_service] = lambda: services.data_controls
    app.dependency_overrides[get_safety_service] = lambda: services.safety
    app.dependency_overrides[get_guardian_service] = lambda: services.guardian

    app.state.member3_services = services

    @app.get("/api/v1/member3/health", tags=["Member 3 - Development"])
    async def member3_health() -> dict[str, object]:
        return {
            "module": "Member 3 - AI Guardian and Safety",
            "status": "running",
            "external_connectors_enabled": False,
            "persistence": "in_memory",
        }

    return app
