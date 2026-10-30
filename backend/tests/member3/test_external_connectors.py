import io
import json

from ai.assistant.openai_provider import OpenAIResponsesProvider
from ai.assistant.provider import EvidenceSummary, StructuredPromptContext
from app.schemas.member3.alerts import AlertPriority
from app.schemas.member3.notifications import NotificationChannel, NotificationCreateRequest, NotificationStatus
from app.services.member3.connectors.base import DeliveryResult
from app.services.member3.connectors.dispatcher import NotificationDispatcher
from app.services.member3.guardian.notification_service import NotificationService


class _Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def test_openai_provider_uses_responses_api_without_storage(monkeypatch):
    captured = {}
    def fake_open(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        return _Response(json.dumps({"output_text": "Evidence-based explanation. This is not a diagnosis."}).encode())
    monkeypatch.setattr("ai.assistant.openai_provider.urlopen", fake_open)
    provider = OpenAIResponsesProvider(api_key="test-key", model="test-model")
    answer = provider.generate(StructuredPromptContext(
        safety_action="observe", safety_reason="Small change",
        evidence=(EvidenceSummary(metric="heart_rate", current_value=82, baseline_value=76, unit="bpm", direction="elevated", confidence=0.9, signal_quality=0.9),),
        user_question="Why did this change?",
    ))
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["payload"]["store"] is False
    assert captured["payload"]["model"] == "test-model"
    assert "not a diagnosis" in answer


class _Connector:
    def __init__(self, result): self.result = result
    def send(self, notification): return self.result


def _notification(service):
    return service.create(NotificationCreateRequest(
        user_id="user-a", source_event_id="event-1", title="Check reading", body="Please review",
        priority=AlertPriority.HIGH, channels=[NotificationChannel.PUSH],
        consented_channels=[NotificationChannel.PUSH], channel_targets={NotificationChannel.PUSH: "opaque-device-token"},
    )).notifications[0]


def test_dispatcher_records_provider_delivery_receipt():
    service = NotificationService()
    notification = _notification(service)
    result = NotificationDispatcher(service, {NotificationChannel.PUSH: _Connector(DeliveryResult(True, "receipt-1"))}).dispatch(notification.notification_id)
    assert result.status == NotificationStatus.DELIVERED
    assert result.provider_receipt_id == "receipt-1"


def test_dispatcher_records_failure_for_retry():
    service = NotificationService()
    notification = _notification(service)
    result = NotificationDispatcher(service, {NotificationChannel.PUSH: _Connector(DeliveryResult(False, failure_reason="temporary"))}).dispatch(notification.notification_id)
    assert result.status == NotificationStatus.FAILED
    queued = service.retry(notification.notification_id)
    assert queued.status == NotificationStatus.QUEUED
