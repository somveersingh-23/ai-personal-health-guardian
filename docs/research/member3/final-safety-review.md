# Member 3 final safety review

## Automated findings

- Safety actions are produced by deterministic rules, not by the LLM.
- Prompt-injection tests verify that user text cannot change the upstream action.
- Emergency workflows record intent and require human confirmation; they do not
  claim that a call or caregiver message happened.
- JWT validation, user-ID matching, data export, and deletion paths have tests.
- Provider credentials are environment-only and are not committed.

## Release blockers requiring people or hardware

1. The bundled knowledge base is labelled project-reviewed prototype guidance.
   It has no authoritative source URLs and no `clinically_approved` sign-off.
   It must not be represented as clinically reviewed.
2. A qualified clinician must approve medical wording and each knowledge chunk.
3. A security reviewer must threat-model the combined application after shared
   authentication and router integration.
4. Android UI, notifications, offline behavior, and emergency affordances need
   emulator plus physical-device accessibility/usability testing.
5. FCM and SMS staging credentials are required for delivery callback tests.

The production release gate must remain closed until these items are recorded
as completed by the responsible reviewers.
