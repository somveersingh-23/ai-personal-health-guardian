import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
    SqlAlertRepository, SqlConversationRepository, SqlEmergencyRepository,
    SqlInsightRepository, SqlNotificationRepository,
)


def create_member3_engine(database_url: str) -> Engine:
    options = {"pool_pre_ping": True}
    if database_url == "sqlite+pysqlite:///:memory:":
        options.update({"connect_args": {"check_same_thread": False}, "poolclass": StaticPool})
    return create_engine(database_url, **options)


def build_persistent_container(engine: Engine, *, create_schema: bool = False) -> Member3ServiceContainer:
    if create_schema:
        Member3Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    provider = OpenAIResponsesProvider() if os.environ.get("MEMBER3_ASSISTANT_PROVIDER") == "openai" else None
    explanation = ExplanationService(provider=provider)
    insights = InsightService(SqlInsightRepository(sessions))
    alerts = AlertService(SqlAlertRepository(sessions))
    notifications = NotificationService(SqlNotificationRepository(sessions))
    caregivers = CaregiverService()
    emergency = EmergencyWorkflowService(SqlEmergencyRepository(sessions), caregiver_validator=caregivers.is_active)
    conversations = ConversationService(explanation, SqlConversationRepository(sessions))
    guardian = GuardianOrchestrationService(
        insight_service=insights, alert_service=alerts,
        notification_service=notifications, emergency_service=emergency,
    )
    data_controls = DataControlService(
        insights=insights, alerts=alerts, notifications=notifications,
        emergency=emergency, conversations=conversations, guardian=guardian,
    )
    return Member3ServiceContainer(
        explanation=explanation, retrieval=get_retrieval_service(), insights=insights,
        alerts=alerts, notifications=notifications, emergency=emergency,
        conversations=conversations, data_controls=data_controls,
        safety=SafetyEvaluationService(), caregivers=caregivers, guardian=guardian,
    )
