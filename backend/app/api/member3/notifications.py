"""Member 3 notification intent and receipt API."""

from __future__ import annotations

import hmac
import os
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.schemas.member3.notifications import (
    DeliveryReceiptRequest,
    NotificationBatchResponse,
    NotificationCreateRequest,
    NotificationListResponse,
    NotificationRecord,
)
from app.services.member3.guardian.notification_service import (
    InvalidNotificationTransitionError,
    NotificationNotFoundError,
    NotificationRetryLimitError,
    NotificationService,
)

router = APIRouter(prefix="/api/v1/member3/notifications", tags=["Member 3 - Notifications"])
_service = NotificationService()


def get_notification_service() -> NotificationService:
    return _service


@router.post("", response_model=NotificationBatchResponse)
async def create_notifications(
    request: NotificationCreateRequest,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationBatchResponse:
    return service.create(request)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    user_id: str = Query(min_length=1, max_length=128),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    try:
        return service.list_notifications(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{notification_id}/dispatch", response_model=NotificationRecord)
async def request_dispatch(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRecord:
    return _handle(lambda: service.request_dispatch(notification_id))


@router.post("/{notification_id}/receipt", response_model=NotificationRecord)
async def record_receipt(
    notification_id: str,
    request: DeliveryReceiptRequest,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRecord:
    return _handle(lambda: service.record_receipt(notification_id, request))


@router.post("/{notification_id}/callback", response_model=NotificationRecord)
async def provider_callback(
    notification_id: str,
    request: DeliveryReceiptRequest,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRecord:
    expected = os.environ.get("MEMBER3_WEBHOOK_SECRET")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification webhook authentication is not configured",
        )
    if not x_webhook_secret or not hmac.compare_digest(x_webhook_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature/secret",
        )
    return _handle(lambda: service.record_receipt(notification_id, request))


@router.post("/{notification_id}/retry", response_model=NotificationRecord)
async def retry_notification(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRecord:
    return _handle(lambda: service.retry(notification_id))


@router.post("/{notification_id}/cancel", response_model=NotificationRecord)
async def cancel_notification(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRecord:
    return _handle(lambda: service.cancel(notification_id))


def _handle(operation):  # noqa: ANN001
    try:
        return operation()
    except NotificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidNotificationTransitionError, NotificationRetryLimitError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
