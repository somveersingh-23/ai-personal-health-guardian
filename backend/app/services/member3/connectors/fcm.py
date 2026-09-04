from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.services.member3.connectors.base import DeliveryResult


class FcmConnector:
    def __init__(self, *, project_id: str | None = None, access_token: str | None = None, timeout: float = 15.0):
        self._project = project_id or os.environ.get("FCM_PROJECT_ID", "")
        self._token = access_token or os.environ.get("FCM_ACCESS_TOKEN", "")
        self._timeout = timeout

    def send(self, notification) -> DeliveryResult:
        if not self._project or not self._token or not notification.target_ref:
            return DeliveryResult(False, failure_reason="FCM connector is not configured")
        payload = {"message": {"token": notification.target_ref, "notification": {"title": notification.title, "body": notification.body}, "data": {"notification_id": notification.notification_id}}}
        request = Request(
            f"https://fcm.googleapis.com/v1/projects/{self._project}/messages:send",
            data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                receipt = json.load(response).get("name")
            return DeliveryResult(True, receipt_id=receipt or notification.notification_id)
        except HTTPError as exc:
            return DeliveryResult(False, failure_reason=f"FCM rejected request ({exc.code})")
        except (URLError, TimeoutError, ValueError):
            return DeliveryResult(False, failure_reason="FCM is unavailable")
