# Member 3 AI Guardian — Assistant API

**Module**: Member 3 · AI Guardian Assistant
**Endpoint**: `POST /api/v1/member3/assistant/explain`
**Branch**: `feature/m3-ai-assistant-api`

---

## Overview

The AI Guardian assistant accepts structured health evidence and a
pre-computed `SafetyDecision` from the Member 3 safety engine and returns
a calm, evidence-grounded explanation.

### Safety guarantees (hard constraints)

| Constraint | Enforced by |
|---|---|
| Never diagnoses a medical condition | System prompt + TemplateProvider templates |
| Never calculates medical risk | Explanation service — no arithmetic on decision |
| Never changes the `safety_action` | Service always echoes input action verbatim |
| Never invents sensor evidence | Provider receives only `StructuredPromptContext.evidence` |
| Never claims certainty when quality/confidence is limited | Service surfaces limitations; template includes uncertainty note |
| Never recommends prescription medication | Templates never mention medications |
| Never replaces emergency care | Emergency services recommended only on `emergency_escalation` |
| Disclaimer always present | Service and TemplateProvider both append it |

---

## Endpoint

```
POST /api/v1/member3/assistant/explain
Content-Type: application/json
```

---

## Request

### Schema — `ExplainRequest`

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | `string` | ✅ | Opaque user identifier |
| `question` | `string` (min 1 char) | ✅ | User's health question (treated as untrusted content) |
| `evidence` | `array[EvidenceItem]` (min 1) | ✅ | Structured health measurements |
| `safety_action` | `string` | ✅ | `SafetyAction` value from the safety engine |
| `safety_reason` | `string` | ✅ | Reason string from the safety engine |
| `conversation_id` | `string` | ❌ | Auto-generated UUID4 if omitted |
| `locale` | `string` | ❌ | BCP-47 locale, default `"en"` |

### `EvidenceItem` schema

| Field | Type | Required | Validation |
|---|---|---|---|
| `metric` | `string` (min 1 char) | ✅ | Name of the health metric |
| `current_value` | `float` | ✅ | Must be finite |
| `baseline_value` | `float` | ✅ | Must be finite |
| `unit` | `string` (min 1 char) | ✅ | Unit of measurement |
| `direction` | `string` (min 1 char) | ✅ | Trend description |
| `confidence` | `float` in `[0, 1]` | ✅ | Must be finite, not NaN or ±Inf |
| `signal_quality` | `float` in `[0, 1]` | ✅ | Must be finite, not NaN or ±Inf |
| `timestamp` | `datetime` (ISO 8601) | ❌ | When the measurement was taken |

### Valid `safety_action` values

| Value | Meaning |
|---|---|
| `normal` | No meaningful deviation |
| `observe` | Small change to monitor |
| `re_measure` | Evidence too unreliable |
| `self_care` | Moderate deviation, self-care steps |
| `caregiver_alert` | Needs caregiver / clinician review |
| `emergency_escalation` | Immediate emergency help required |

### Example request

```json
{
  "user_id": "user-001",
  "question": "Why is my heart rate elevated?",
  "evidence": [
    {
      "metric": "heart_rate",
      "current_value": 96,
      "baseline_value": 72,
      "unit": "bpm",
      "direction": "elevated",
      "confidence": 0.88,
      "signal_quality": 0.91,
      "timestamp": "2026-08-30T10:00:00Z"
    }
  ],
  "safety_action": "observe",
  "safety_reason": "Small deviation detected above baseline.",
  "locale": "en"
}
```

---

## Response

### Schema — `ExplainResponse`

| Field | Type | Description |
|---|---|---|
| `conversation_id` | `string` | Conversation tracking ID |
| `answer` | `string` | The generated health explanation |
| `safety_action` | `string` | Echoes the input action **unchanged** |
| `evidence_used` | `array[string]` | Metric names referenced in the answer |
| `limitations` | `array[string]` | Evidence quality caveats |
| `disclaimer` | `string` | Medical disclaimer (always present) |
| `generated_at` | `datetime` | UTC generation timestamp |

### Example response

```json
{
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "answer": "A small change has been noticed in your health indicators. No immediate action is needed, but it is worth keeping an eye on how things develop over the next few days.\n\nHere is what your data shows:\n  • your heart_rate is elevated (current: 96.0 bpm, baseline: 72.0 bpm).\n\nMonitor your readings over the next 24–48 hours. If the change persists or worsens, contact your healthcare provider.\n\nImportant: This is a safety-oriented health insight, not a medical diagnosis or professional medical advice. Always consult a qualified healthcare professional before making any health decisions.",
  "safety_action": "observe",
  "evidence_used": ["heart_rate"],
  "limitations": [],
  "disclaimer": "Important: This is a safety-oriented health insight, not a medical diagnosis or professional medical advice. Always consult a qualified healthcare professional before making any health decisions.",
  "generated_at": "2026-08-30T10:00:05Z"
}
```

---

## Error Responses

| HTTP Code | Trigger |
|---|---|
| `422 Unprocessable Entity` | Pydantic validation failure (empty question, invalid evidence, NaN/Inf, etc.) |
| `422 Unprocessable Entity` | Unrecognised `safety_action` value |
| `422 Unprocessable Entity` | All evidence items have blank metric names |
| `500 Internal Server Error` | Assistant provider raised an unexpected error |

---

## Provider Abstraction

The service uses a **provider abstraction** (`AssistantProvider` protocol in `ai/assistant/provider.py`) with dependency injection.

### Adding a real LLM provider

1. Create a new class in `ai/assistant/` (e.g. `openai_provider.py`) that implements:

   ```python
   def generate(self, context: StructuredPromptContext) -> str:
       ...
   ```

2. Override the FastAPI dependency in `backend/app/api/member3/assistant.py`:

   ```python
   def get_explanation_service() -> ExplanationService:
       return ExplanationService(provider=OpenAIProvider(api_key=...))
   ```

No changes to the service contract or router are required.

---

## Running Tests

```bash
# From the repository root
python -m pytest backend/tests/member3/ -v
```

Expected output: all Member 3 tests pass (safety engine + assistant tests), no external network required.

---

## Router Registration in `main.py`

> **Note**: `main.py` is owned by Member 1. Do not edit it directly.
> Provide this snippet to Member 1 for integration:

```python
# Add this import at the top of backend/app/main.py
from app.api.member3.assistant import router as assistant_router

# Add this include_router call after the existing includes
app.include_router(assistant_router)
```

Full example of the relevant section of `main.py` after integration:

```python
from app.api.member1.health_profile import router as health_profile_router
from app.api.member3.assistant import router as assistant_router   # Member 3

app.include_router(health_profile_router)
app.include_router(assistant_router)                               # Member 3
```

---

## Architecture Diagram

```
POST /api/v1/member3/assistant/explain
           │
           ▼
   ExplainRequest (Pydantic)
   - validates numeric bounds
   - rejects NaN / Infinity
   - auto-generates conversation_id
           │
           ▼
   ExplanationService.explain()
   - validates safety_action ∈ SafetyAction
   - normalises evidence (strips blank metrics)
   - builds StructuredPromptContext (frozen)
   - sanitises user question (injection protection)
           │
           ▼
   AssistantProvider.generate(context)
   [TemplateProvider by default — no API key]
           │
           ▼
   ExplainResponse
   - safety_action echoed unchanged
   - evidence_used ⊆ supplied metrics
   - disclaimer always present
```
