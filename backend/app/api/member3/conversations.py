"""Member 3 AI Guardian conversation API."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.member3.conversations import (
    ConversationDeleteResponse,
    ConversationListResponse,
    ConversationMessageRequest,
    ConversationRecord,
)
from app.services.member3.guardian.conversation_service import (
    ConversationNotFoundError,
    ConversationOwnershipError,
    ConversationService,
)

router = APIRouter(prefix="/api/v1/member3/conversations", tags=["Member 3 - Conversations"])
_service = ConversationService()


def get_conversation_service() -> ConversationService:
    return _service


@router.post("/messages", response_model=ConversationRecord)
async def send_message(
    request: ConversationMessageRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationRecord:
    return _handle(lambda: service.send(request))


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str = Query(min_length=1, max_length=128),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    return service.list_conversations(user_id)


@router.get("/{conversation_id}", response_model=ConversationRecord)
async def get_conversation(
    conversation_id: str,
    user_id: str = Query(min_length=1, max_length=128),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationRecord:
    return _handle(lambda: service.get(conversation_id, user_id))


@router.delete("/{conversation_id}", response_model=ConversationDeleteResponse)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Query(min_length=1, max_length=128),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationDeleteResponse:
    return _handle(lambda: service.delete(conversation_id, user_id))


def _handle(operation):  # noqa: ANN001
    try:
        return operation()
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConversationOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
