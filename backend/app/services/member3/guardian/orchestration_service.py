"""Connect all Member 3 modules without changing upstream risk decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Callable

from app.schemas.member3.alerts import AlertEvaluationRequest
from app.schemas.member3.emergency import EmergencyStartRequest
from app.schemas.member3.guardian import GuardianProcessRequest, GuardianProcessResponse
from app.schemas.member3.insights import InsightCreateRequest
from app.schemas.member3.notifications import NotificationCreateRequest
from app.services.member3.guardian.alert_service import AlertService
from app.services.member3.guardian.emergency_service import EmergencyWorkflowService
from app.services.member3.guardian.insight_service import InsightService
from app.services.member3.guardian.notification_service import NotificationService
from ml.safety import SafetyAction, SafetyEngine, SafetyInput


class GuardianOrchestrationService:
    """Run the deterministic Member 3 product loop once per user event."""

    def __init__(
        self,
        safety_engine: SafetyEngine | None = None,
        insight_service: InsightService | None = None,
        alert_service: AlertService | None = None,
        notification_service: NotificationService | None = None,
        emergency_service: EmergencyWorkflowService | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._safety = safety_engine or SafetyEngine()
        self._insights = insight_service or InsightService()
        self._alerts = alert_service or AlertService()
        self._notifications = notification_service or NotificationService()
        self._emergency = emergency_service or EmergencyWorkflowService()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._processed: dict[tuple[str, str], GuardianProcessResponse] = {}
        self._lock = RLock()

    def process(self, request: GuardianProcessRequest) -> GuardianProcessResponse:
        key = (request.user_id, request.event_id)
        with self._lock:
            existing = self._processed.get(key)
            if existing is not None:
                return existing

            evidence_text = tuple(
                f"{item.metric}: {item.direction}" for item in request.evidence
            )
            decision = self._safety.evaluate(
                SafetyInput.from_evidence(
                    deviation_score=request.deviation_score,
                    confidence=request.confidence,
                    signal_quality=request.signal_quality,
                    evidence=evidence_text,
                    critical_flags=request.critical_flags,
                    user_confirmed_severe_symptoms=request.user_confirmed_severe_symptoms,
                )
            )

            insight = self._insights.create(
                InsightCreateRequest(
                    user_id=request.user_id,
                    source_event_id=request.event_id,
                    insight_type=request.insight_type,
                    safety_action=decision.action,
                    safety_reason=decision.reason,
                    evidence=request.evidence,
                )
            )

            alert = self._alerts.evaluate(
                AlertEvaluationRequest(
                    user_id=request.user_id,
                    event_id=request.event_id,
                    safety_action=decision.action,
                    safety_reason=decision.reason,
                    evidence=list(decision.evidence) or list(evidence_text),
                    occurred_at=request.occurred_at,
                )
            )

            notifications = None
            emergency = None
            if alert.created and alert.alert is not None:
                notifications = self._notifications.create(
                    NotificationCreateRequest(
                        user_id=request.user_id,
                        source_event_id=request.event_id,
                        title=alert.alert.title,
                        body=alert.alert.message,
                        priority=alert.alert.priority,
                        channels=request.notification_channels,
                        consented_channels=request.consented_channels,
                        channel_targets=request.channel_targets,
                    )
                )
                if decision.action == SafetyAction.EMERGENCY_ESCALATION:
                    emergency = self._emergency.start(
                        EmergencyStartRequest(
                            user_id=request.user_id,
                            alert_id=alert.alert.alert_id,
                            safety_action=decision.action,
                            safety_reason=decision.reason,
                            evidence=list(decision.evidence) or list(evidence_text),
                            caregiver_contact_id=request.caregiver_contact_id,
                        )
                    )

            response = GuardianProcessResponse(
                user_id=request.user_id,
                event_id=request.event_id,
                safety_action=decision.action,
                safety_reason=decision.reason,
                insight=insight,
                alert=alert,
                notifications=notifications,
                emergency_workflow=emergency,
                processed_at=self._utc(self._clock()),
            )
            self._processed[key] = response
            return response

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
