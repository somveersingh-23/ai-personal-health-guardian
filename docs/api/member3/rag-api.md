# Member 3 RAG API

## Purpose and Limitations
The Member 3 RAG API provides contextual educational information from an approved local knowledge base to augment AI responses. It is strictly limited to returning non-medical educational content.

## Architecture
The API uses a deterministic, offline keyword-based retrieval mechanism. It does not use vector embeddings, external services, or LLM APIs.

## Endpoint Specification
**POST** `/api/v1/member3/rag/retrieve`

### Request
```json
{
  "question": "How does sleep and hydration affect my heart rate?",
  "topics": ["sleep_and_recovery", "hydration"],
  "locale": "en",
  "top_k": 3
}
```
*Note*: When multiple topics are provided in `topics`, OR semantics are used (chunks matching any of the requested topics are candidates).

### Response
```json
{
  "query": "How does sleep affect my heart rate?",
  "results": [
    {
      "document_id": "doc_sleep_001",
      "chunk_id": "chunk_sleep_001_01",
      "title": "Sleep and Recovery",
      "passage": "Adequate sleep supports heart rate stability...",
      "topic": "sleep_and_recovery",
      "source_name": "Project-reviewed prototype guidance",
      "source_url": null,
      "reviewed_at": "2026-08-01",
      "score": 4.5
    }
  ],
  "result_count": 1,
  "limitations": [
    "Retrieved passages are educational reference content only..."
  ],
  "generated_at": "2026-08-30T10:00:00Z"
}
```

## Scoring Algorithm Overview
- title match: 3.0 per matching token
- topic match: 2.5 per matching token
- keyword match: 2.0 per matching token
- content match: 1.0 per matching token

## Review-status Filtering
Only chunks with `review_status == "approved"` and `expires_on` absent or in the future are returned.

## Error Table
| Status | Condition |
|--------|-----------|
| 200    | Success (even if 0 results) |
| 422    | Invalid request parameters |
| 500    | Internal failure (e.g. malformed KB) |

## Privacy and Safety Constraints
- Passages are sanitized for injection attempts.
- No network requests are made.

## Testing Command
```bash
python -m pytest backend/tests/member3/test_rag.py -v
```

## Router Registration Snippet (main.py)
```python
from app.api.member3.rag import router as rag_router
app.include_router(rag_router)
```
