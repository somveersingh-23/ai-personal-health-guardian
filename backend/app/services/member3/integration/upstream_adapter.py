import math
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
        if sensors.user_id is not None and baseline.user_id != sensors.user_id:
            raise UpstreamContractError(
                f"Baseline user_id '{baseline.user_id}' does not match sensor user_id '{sensors.user_id}'"
            )
        if baseline.event_id != sensors.event_id:
            raise UpstreamContractError("Baseline and sensor results must reference the same event_id")

        for name, value in (
            ("current", baseline.current),
            ("baseline", baseline.baseline),
            ("deviation_score", baseline.deviation_score),
            ("confidence", baseline.confidence),
            ("fusion_confidence", sensors.fusion_confidence),
            ("signal_quality", sensors.signal_quality),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise UpstreamContractError(f"Field '{name}' must be a finite number")

        if not (0.0 <= baseline.confidence <= 1.0):
            raise UpstreamContractError("baseline confidence must be in range [0.0, 1.0]")
        if not (0.0 <= sensors.fusion_confidence <= 1.0):
            raise UpstreamContractError("sensors fusion_confidence must be in range [0.0, 1.0]")
        if not (0.0 <= sensors.signal_quality <= 1.0):
            raise UpstreamContractError("sensors signal_quality must be in range [0.0, 1.0]")

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
