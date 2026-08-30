# Member 3 Conversations API

This API adds multi-turn history around the existing safe explanation service.
Messages are idempotent per user and message ID. Conversation reads and deletes
are user-scoped, and deletion removes both history and idempotency indexes.

Endpoints:

- `POST /api/v1/member3/conversations/messages`
- `GET /api/v1/member3/conversations?user_id=...`
- `GET /api/v1/member3/conversations/{id}?user_id=...`
- `DELETE /api/v1/member3/conversations/{id}?user_id=...`

Storage is in-memory. Production integration requires authenticated user IDs,
encrypted persistence, retention limits, export tooling, and audit controls.
