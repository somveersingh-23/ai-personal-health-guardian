import os

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import sessionmaker

from app.api.member3.app import Member3ServiceContainer
from app.api.member3.rag import get_retrieval_service
from ai.assistant.openai_provider import OpenAIResponsesProvider
from app.models.member3.guardian_record import Member3Base
from app.services.member3.guardian.alert_service import AlertService
from app.services.member3.guardian.caregiver_service import CaregiverService
from app.services.member3.guardian.conversation_service import ConversationService
from app.services.member3.guardian.data_control_service import DataControlService
from app.services.member3.guardian.emergency_service import EmergencyWorkflowService
from app.services.member3.guardian.explanation_service import ExplanationService
from app.services.member3.guardian.insight_service import InsightService
from app.services.member3.guardian.notification_service import NotificationService
from app.services.member3.guardian.orchestration_service import GuardianOrchestrationService
from app.services.member3.guardian.safety_service import SafetyEvaluationService
from app.services.member3.persistence.repositories import (
    SqlAlertRepository, SqlCaregiverRepository, SqlConversationRepository,
    SqlEmergencyRepository, SqlGuardianOrchestrationRepository,
    SqlInsightRepository, SqlNotificationRepository,
    resolve_sync_engine,
)


def create_member3_engine(database_url: str) -> Engine:
    """Create a synchronous SQLAlchemy Engine for Member 3 persistence."""
    return resolve_sync_engine(database_url)


def build_persistent_container(
    engine: Engine | AsyncEngine | str,
    *,
    create_schema: bool = False,
) -> Member3ServiceContainer:
    """Construct a full Member 3 service container backed by durable database tables."""
    sync_engine = resolve_sync_engine(engine)
    if create_schema:
        Member3Base.metadata.create_all(sync_engine)
    sessions = sessionmaker(sync_engine, expire_on_commit=False)
    provider = OpenAIResponsesProvider() if os.environ.get("MEMBER3_ASSISTANT_PROVIDER") == "openai" else None
    retrieval = get_retrieval_service()
    explanation = ExplanationService(provider=provider, retrieval_service=retrieval)
    insights = InsightService(SqlInsightRepository(sessions))
    alerts = AlertService(SqlAlertRepository(sessions))
    notifications = NotificationService(SqlNotificationRepository(sessions))
    caregivers = CaregiverService(SqlCaregiverRepository(sessions))
    emergency = EmergencyWorkflowService(SqlEmergencyRepository(sessions), caregiver_validator=caregivers.is_active)
    conversations = ConversationService(explanation, SqlConversationRepository(sessions))
    guardian = GuardianOrchestrationService(
        insight_service=insights, alert_service=alerts,
        notification_service=notifications, emergency_service=emergency,
        repository=SqlGuardianOrchestrationRepository(sessions),
    )
    data_controls = DataControlService(
        insights=insights, alerts=alerts, notifications=notifications,
        emergency=emergency, conversations=conversations, guardian=guardian,
        caregivers=caregivers,
    )
    return Member3ServiceContainer(
        explanation=explanation, retrieval=retrieval, insights=insights,
        alerts=alerts, notifications=notifications, emergency=emergency,
        conversations=conversations, data_controls=data_controls,
        safety=SafetyEvaluationService(), caregivers=caregivers, guardian=guardian,
    )
