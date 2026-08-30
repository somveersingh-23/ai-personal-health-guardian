# Member 3 Data Controls

- `GET /api/v1/member3/data/export?user_id=...` exports all Member 3-held data.
- `DELETE /api/v1/member3/data?user_id=...` purges insights, alerts,
  notifications, emergency workflows, conversations, indexes, and orchestration cache.

These development endpoints rely on a supplied user ID. Production use must
require authenticated ownership, re-authentication for deletion, encrypted
exports, persistent-database transactions, and auditable retention policies.
