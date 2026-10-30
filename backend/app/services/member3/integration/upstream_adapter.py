import hashlib
import json
import math
from app.schemas.member3.assistant import EvidenceItem
from app.schemas.member3.guardian import GuardianProcessRequest
from app.schemas.member3.notifications import NotificationChannel
from app.schemas.member3.upstream import (
    BaselineResult,
    M2MultimodalEvidenceVector,
    SensorIntelligenceResult,
)


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

    def build_from_evidence_vector(
        self,
        vector: M2MultimodalEvidenceVector,
        *,
        user_confirmed_severe_symptoms: bool = False,
        channels: list[NotificationChannel] | None = None,
        consented_channels: list[NotificationChannel] | None = None,
        channel_targets: dict[NotificationChannel, str] | None = None,
        caregiver_contact_id: str | None = None,
    ) -> GuardianProcessRequest:
        """Translate the canonical M2 v2 evidence vector without inventing raw values.

        Evidence strength remains provenance only. M3 derives conservative safety
        inputs from individual weights; it never treats strength as disease risk.
        """

        direction_map = {
            "below": "decreased",
            "normal": "stable",
            "above": "elevated",
            "unknown": "unknown",
        }
        evidence = [
            EvidenceItem(
                metric=item.metric,
                standardized_deviation=item.standardized_deviation,
                direction=direction_map[item.direction],
                confidence=item.evidence_weight,
                signal_quality=item.quality_weight,
                timestamp=vector.window_end,
            )
            for item in vector.evidence
        ]

        deviation_score = max(
            (abs(item.standardized_deviation) for item in vector.evidence),
            default=0.0,
        )
        confidence = min((item.evidence_weight for item in vector.evidence), default=0.0)
        signal_quality = min((item.quality_weight for item in vector.evidence), default=0.0)
        if vector.abstained:
            deviation_score = 0.0
            confidence = 0.0
            signal_quality = 0.0

        selected = channels or [NotificationChannel.IN_APP]
        consented = consented_channels or [NotificationChannel.IN_APP]
        return GuardianProcessRequest(
            user_id=str(vector.user_id),
            event_id=self._event_id(vector),
            insight_type="multimodal_health_change",
            deviation_score=deviation_score,
            confidence=confidence,
            signal_quality=signal_quality,
            evidence=evidence,
            # M2 explicitly does not own emergency classification.
            critical_flags=[],
            user_confirmed_severe_symptoms=user_confirmed_severe_symptoms,
            occurred_at=vector.window_end,
            notification_channels=selected,
            consented_channels=consented,
            channel_targets=channel_targets or {},
            caregiver_contact_id=caregiver_contact_id,
            source_schema_version=vector.schema_version,
            upstream_abstained=vector.abstained,
            abstention_reasons=list(vector.abstention_reasons),
            missing_baselines=[str(item) for item in vector.missing_baselines],
            non_diagnostic=vector.non_diagnostic,
        )

    @staticmethod
    def _event_id(vector: M2MultimodalEvidenceVector) -> str:
        payload = vector.model_dump(mode="json")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "m2ev-" + hashlib.sha256(encoded).hexdigest()[:32]
