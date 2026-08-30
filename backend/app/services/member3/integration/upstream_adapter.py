from app.schemas.member3.assistant import EvidenceItem
from app.schemas.member3.guardian import GuardianProcessRequest
from app.schemas.member3.notifications import NotificationChannel
from app.schemas.member3.upstream import BaselineResult, SensorIntelligenceResult


class UpstreamContractError(ValueError):
    pass


class UpstreamGuardianAdapter:
    """Join agreed Member 1/2 outputs into the Member 3 orchestration request."""

    def build(
        self,
        baseline: BaselineResult,
        sensors: SensorIntelligenceResult,
        *,
        channels: list[NotificationChannel] | None = None,
        consented_channels: list[NotificationChannel] | None = None,
        channel_targets: dict[NotificationChannel, str] | None = None,
        caregiver_contact_id: str | None = None,
    ) -> GuardianProcessRequest:
        if baseline.event_id != sensors.event_id:
            raise UpstreamContractError("Baseline and sensor results must reference the same event_id")
        direction = {
            "above_normal": "elevated", "below_normal": "decreased",
            "normal": "stable", "unknown": "unknown",
        }.get(baseline.status.lower(), "changed")
        evidence = EvidenceItem(
            metric=baseline.metric, current_value=baseline.current,
            baseline_value=baseline.baseline, unit=baseline.unit,
            direction=direction, confidence=min(baseline.confidence, sensors.fusion_confidence),
            signal_quality=sensors.signal_quality, timestamp=baseline.occurred_at,
        )
        selected = channels or [NotificationChannel.IN_APP]
        consented = consented_channels or [NotificationChannel.IN_APP]
        return GuardianProcessRequest(
            user_id=baseline.user_id, event_id=baseline.event_id,
            insight_type="health_change", deviation_score=baseline.deviation_score,
            confidence=evidence.confidence, signal_quality=evidence.signal_quality,
            evidence=[evidence], critical_flags=sensors.critical_flags,
            user_confirmed_severe_symptoms=sensors.user_confirmed_severe_symptoms,
            occurred_at=baseline.occurred_at, notification_channels=selected,
            consented_channels=consented, channel_targets=channel_targets or {},
            caregiver_contact_id=caregiver_contact_id,
        )
