# Member 3: Safety Engine

This module is owned by Member 3. It accepts structured output from the
baseline and sensor-fusion modules and selects a conservative next action.
It does not diagnose disease and does not allow an LLM to calculate risk.

## Input contract

- `deviation_score`: non-negative upstream deviation score
- `confidence`: upstream confidence from `0.0` to `1.0`
- `signal_quality`: upstream signal quality from `0.0` to `1.0`
- `evidence`: short facts that can later support an explanation
- `critical_flags`: flags produced by validated upstream logic
- `user_confirmed_severe_symptoms`: explicit user confirmation

## Output actions

`normal`, `observe`, `re_measure`, `self_care`, `caregiver_alert`, or
`emergency_escalation`.

The returned `SafetyDecision` also contains a reason, the evidence used, a
human-confirmation flag, and a non-diagnosis disclaimer. The future AI
Guardian should explain this decision without changing its action.
