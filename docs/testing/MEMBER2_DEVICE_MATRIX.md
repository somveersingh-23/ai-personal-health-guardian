# Member 2 Device Validation Matrix

Automated backend status is recorded separately; every row below is a required physical/emulator test and is currently **pending** until evidence (device/build/date/result/log reference) is attached.

| Platform/source | Required scenarios |
|---|---|
| Android 9–13 + Health Connect APK | unavailable/update/install flow, rationale intent, per-type grant/deny, settings/revoke, foreground sync |
| Android 14–17 platform Health Connect | onboarding alias, per-type grant/deny, background/history feature checks, manage-access intent |
| Google Pixel + Pixel Watch/Fitbit | heart-rate series, steps, sleep stages, recording/device provenance, mirrored-source behavior |
| Samsung phone + Galaxy Watch/Samsung Health | supported-type gaps, origin metadata, duplicate/mirrored records, revocation during sync |
| No wearable / partial permissions | explicit missing metrics, no zero imputation, per-type continuation |
| Token unused/invalid for 30+ days | bounded full snapshot, stale deletion reconciliation, no token advance on backend failure |
| Process/network interruption | retry/idempotency after each page, no lost deletion, no duplicate normalized events |
| Large history | page-streamed upload, multi-chunk staged reconciliation, bounded memory, process/network interruption and token-advance proof |
| Camera devices/front-back variations | deny/revoke, lifecycle stop, lighting, blur, clipping, motion, no stored/transmitted frame |
| Battery/background | one-hour Worker policy, battery-not-low constraint, OEM background restriction behavior |

Record sync success rate, elapsed time, bytes, battery delta, record count, missing types and every abstention/failure. Do not record raw health values in validation logs.

Record results in a copy of `member2-device-evidence.example.json` and validate it with:

```powershell
ml\.venv\Scripts\python.exe scripts\validate-member2-device-evidence.py <evidence.json>
```

Use `--require-complete` only for a release gate. The checked-in example remains `pending` because desktop tests cannot manufacture physical-device evidence.
