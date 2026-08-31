"""Aggregate export and purge controls across Member 3 stores."""

from datetime import datetime, timezone

from app.schemas.member3.data_controls import Member3DataExport, Member3PurgeResponse
from app.services.member3.guardian.alert_service import AlertService
from app.services.member3.guardian.caregiver_service import CaregiverService
from app.services.member3.guardian.conversation_service import ConversationService
from app.services.member3.guardian.emergency_service import EmergencyWorkflowService
from app.services.member3.guardian.insight_service import InsightService
from app.services.member3.guardian.notification_service import NotificationService
from app.services.member3.guardian.orchestration_service import GuardianOrchestrationService


class DataControlService:
    def __init__(
        self,
        *,
        insights: InsightService,
        alerts: AlertService,
        notifications: NotificationService,
        emergency: EmergencyWorkflowService,
        conversations: ConversationService,
        guardian: GuardianOrchestrationService,
        caregivers: CaregiverService | None = None,
    ) -> None:
        self.insights, self.alerts, self.notifications = insights, alerts, notifications
        self.emergency, self.conversations, self.guardian = emergency, conversations, guardian
        self.caregivers = caregivers

    def export(self, user_id: str) -> Member3DataExport:
        user_id = _clean(user_id)
        return Member3DataExport(
            user_id=user_id, exported_at=datetime.now(timezone.utc),
            insights=[x.model_dump(mode="json") for x in self.insights.list_insights(user_id).insights],
            alerts=[x.model_dump(mode="json") for x in self.alerts.list_alerts(user_id).alerts],
            notifications=[x.model_dump(mode="json") for x in self.notifications.list_notifications(user_id).notifications],
            emergency_workflows=[x.model_dump(mode="json") for x in self.emergency.list_workflows(user_id).workflows],
            conversations=[x.model_dump(mode="json") for x in self.conversations.list_conversations(user_id).conversations],
        )

    def purge(self, user_id: str) -> Member3PurgeResponse:
        user_id = _clean(user_id)
        counts = {
            "insights": self.insights.purge_user(user_id),
            "alerts": self.alerts.purge_user(user_id),
            "notifications": self.notifications.purge_user(user_id),
            "emergency_workflows": self.emergency.purge_user(user_id),
            "conversations": self.conversations.purge_user(user_id),
            "orchestration_cache": self.guardian.purge_user_cache(user_id),
        }
        if self.caregivers is not None:
            counts["caregivers"] = self.caregivers.purge_user(user_id)
        return Member3PurgeResponse(
            user_id=user_id,
            deleted_counts=counts,
            total_deleted=sum(counts.values()),
            purged_at=datetime.now(timezone.utc),
        )

    def purge_user_data(self, user_id: str) -> int:
        return self.purge(user_id).total_deleted


def _clean(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("user_id must not be blank")
    return value
