from __future__ import annotations

import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.services.member3.connectors.base import DeliveryResult


class TwilioSmsConnector:
    def __init__(self, *, account_sid: str | None = None, auth_token: str | None = None, from_number: str | None = None, timeout: float = 15.0):
        self._sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID", "")
        self._token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN", "")
        self._from = from_number or os.environ.get("TWILIO_FROM_NUMBER", "")
        self._timeout = timeout

    def send(self, notification) -> DeliveryResult:
        if not self._sid or not self._token or not self._from or not notification.target_ref:
            return DeliveryResult(False, failure_reason="SMS connector is not configured")
        credentials = base64.b64encode(f"{self._sid}:{self._token}".encode()).decode()
        request = Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json",
            data=urlencode({"To": notification.target_ref, "From": self._from, "Body": f"{notification.title}: {notification.body}"}).encode(),
            method="POST", headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                receipt = json.load(response).get("sid")
            return DeliveryResult(True, receipt_id=receipt or notification.notification_id)
        except HTTPError as exc:
            return DeliveryResult(False, failure_reason=f"SMS provider rejected request ({exc.code})")
        except (URLError, TimeoutError, ValueError):
            return DeliveryResult(False, failure_reason="SMS provider is unavailable")
