# Member 2 Real-Data Results

Initial acquisition/run date: 2026-08-29. Reports and the added external respiratory/dual-wavelength validations were regenerated and verified through 2026-08-30 UTC. These are engineering/research results, not clinical performance claims.

## Source integrity

| Source | Acquired content | Verified SHA-256 / integrity |
|---|---:|---|
| BIDMC v1.0.0 | 217,902,224-byte official archive; 484 files | `7c09847e8b9c9ad0005ad6f4041e887119e2ad9a745b6a63b1b394bd439f693b`; all 483 publisher-listed file checksums passed |
| PPG-DaLiA v1.0 | 2,865,111,320-byte official outer archive | `5772387956e34e2e2dc4c2ddbeb98cb70569d5112fa4c13ee98a17680b84a1f3` |
| PPG-DaLiA inner `data.zip` | 92 members; 24,134,804,091 uncompressed bytes inspected without full expansion | `fcda4d13f6475e88a24f1ef9658627dc98e04dd5c5dd790cd2b0a1a22e31913b` |
| Sleep-EDF curated PSG | 48,338,048 bytes | `2b40a18adf76af69a42d6db1f30f31d26b369f6d27ca0050ef30147ef892b131` |
| Sleep-EDF curated hypnogram | 4,620 bytes | `a4cf67694ade1b52a0ddd06d5817fd45d2d3e8bac5302f640f3e9cfbbf12a996` |
| CapnoBase v1.1 | 84 original signal/reference CSV files; 104,026,590 bytes | Each publisher MD5 passed; pinned 84-file metadata manifest SHA-256 `15272b91f86047a76b5ef0f9ce803f048b6df20dd68d016bba3acc467e4240de` |
| PhysioNet PTT-PPG v1.1.0 | 66 WFDB recordings plus metadata; 135 files; 437,990,052 bytes | Every selected file passed the official publisher SHA-256 manifest; manifest SHA-256 `02b3393e8aecc711a6ec56c19c1c3c9bb6ac0048691780f2c815318dd5c3a3de` |

Raw and processed research data remains outside Git. The local run used `D:\AIHealthData` via `HEALTH_GUARDIAN_DATA_ROOT`; the repository `data/` path remains the ignored fallback. The PPG-DaLiA minimized cache contains only wrist PPG, acceleration, temperature, activity labels and ECG-derived HR; its 15 files are independently hashed in the local cache manifest.

## Container runtime validation

The isolated runtime smoke test passed on Docker Desktop 4.88.1, Docker Engine 29.7.2 and Compose 5.4.0. It built the backend image from the pinned requirements, started PostgreSQL 16.10, waited for its health check, verified Alembic revision `0002_member2`, all ten expected application tables and the governed-observation columns, then confirmed `/healthz`. An authenticated end-to-end PostgreSQL flow additionally verified the machine-readable camera-SpO2 prohibition, immutable active consent creation, v3 Steps ingestion with canonical UCUM `{count}` and LOINC `41950-7`, consent withdrawal and linked-observation deletion. A dynamically allocated localhost port avoided collision with developer services. The test then removed its containers, network and PostgreSQL volume; only the reusable local image/build cache was retained.

## Production-contract validation

| Dataset | Coverage | Result |
|---|---:|---|
| BIDMC | 53 recordings; 50,758 events (53 HR series, 25,340 RR and 25,365 SpO2 reference events) | Passed `member2-health-event-v2` |
| PPG-DaLiA | 15 participants; 81 events (15 ECG-derived HR series and 66 temperature chunks) | Passed `member2-health-event-v2` |
| Sleep-EDF | One paired PSG/hypnogram and expert-scored session | Paired recording bounds and `member2-health-event-v2` passed |

Four BIDMC recordings contain an isolated out-of-order breath annotation. The adapter deterministically sorts/deduplicates annotation times and records the correction count; waveform and monitor values are unchanged.

## BIDMC held-out external-domain results

The deterministic participant split held out 11 of 53 recordings. The pulse-rate algorithm was not fitted to BIDMC.

| Test | Windows | MAE | RMSE | Within 5 bpm |
|---|---:|---:|---:|---:|
| PPG pulse rate vs ECG-derived HR | 2,607 | 1.99 bpm | 4.00 bpm | 91.83% |
| Impedance respiration vs two manual breath annotators | 583 | 0.61 bpm | 1.32 bpm | 98.63% |
| PPG multimodulation respiration vs two manual breath annotators | 583 | 4.30 bpm | 6.89 bpm | 65.01% |

Decision: baseline/amplitude/frequency fusion is a large improvement over the rejected amplitude-only prototype, but it still has participant-specific failures. The component-agreement subset was worse on BIDMC and is not a validated gate. PPG-derived RR remains research-only and must not be exposed as a product measurement. BIDMC is short critical-care pulse-oximeter data, so these results do not establish wrist-wearable performance.

Participant-level reporting materially changes the interpretation: participant-macro pulse-rate MAE is 1.99 bpm and macro within-5-bpm fraction is 91.83%, but individual performance ranges from 0.95 to 8.25 bpm MAE. Recording 45 reaches only 29.96% within 5 bpm. Aggregate performance must therefore never be presented as uniform subject-level accuracy.

## CapnoBase frozen external respiratory-rate benchmark

The algorithm and 64-second/8-second-stride protocol were frozen before CapnoBase was evaluated. All 42 cases were used only as a benchmark; no training, coefficient tuning, or threshold selection used these records. Sixteen non-finite or out-of-supported-band reference points were transparently excluded, producing 2,202 usable windows and 24 reference-sparse failed windows.

| Windows | MAE | RMSE | Median absolute error | P95 absolute error | Within 5 bpm |
|---:|---:|---:|---:|---:|---:|
| 2,202 | 3.74 bpm | 9.45 bpm | 0.23 bpm | 21.58 bpm | 81.06% |

Decision: the low median error demonstrates real respiratory information in PPG, while the high RMSE/p95 exposes severe tail failures. Case-macro MAE is 3.76 bpm. Component agreement improved this external subset but failed to improve BIDMC, so it cannot be promoted to a general acceptance gate. These anaesthesia-domain results do not establish wrist-wearable or clinical performance.

## Real paired optical-channel PPG validation

PhysioNet PTT-PPG supplied 66 recordings from 22 healthy participants with paired red/infrared optical channels at distal and proximal sites sampled at 500 Hz. Its official README is internally inconsistent: the hardware section labels `pleth_1/4` infrared and `pleth_2/5` red, while the data-description section states the reverse. The adapter therefore preserves wavelength-neutral channel order and blocks wavelength-specific calibration. The full non-overlapping 8-second run processed 8,028 channel-pair windows with zero processing failures.

| Slice | Windows | Usable coverage |
|---|---:|---:|
| Overall | 8,028 | 83.12% |
| Distal sensor | 4,014 | 89.54% |
| Proximal sensor | 4,014 | 76.71% |
| Sitting | 2,678 | 91.08% |
| Walking | 2,666 | 74.57% |
| Running | 2,684 | 83.68% |

Decision: real paired-channel loading, synchronization, AC/DC ratio features, perfusion, cross-channel correlation, spectral quality checks, and abstention are implemented and verified. Ratio orientation is descriptive only until the publisher mapping conflict is resolved. The only SpO2 metadata are boundary spot checks from 94% to 99%; they are neither continuous nor synchronized arterial references and do not cover hypoxaemia. Therefore zero numeric SpO2 values were emitted and no calibration was fitted. A device-specific calibration study with verified wavelength mapping and synchronized co-oximetry/arterial reference across the intended saturation range remains mandatory.

## PPG-DaLiA participant-held-out results

The official 8-second window / 2-second stride alignment produced 64,697 windows with zero processing failures. Participants were split 9 train / 3 validation / 3 untouched test. Preprocessing and the logistic quality model were fitted only on training participants; the threshold was selected only on validation participants.

### Baseline pulse-rate estimator

| Split | Windows | MAE | Within 5 bpm |
|---|---:|---:|---:|
| Train | 40,531 | 19.96 bpm | 49.88% |
| Validation | 12,942 | 15.17 bpm | 56.68% |
| Test | 11,224 | 16.23 bpm | 53.85% |

The ungated spectral baseline is not acceptable for product use during unrestricted daily activity.

### Motion/signal-quality gate

Validation selected threshold `0.7498666944`, reaching 90.01% accepted-window precision at 29.00% coverage. On untouched test participants:

- acceptance coverage: 31.99% (3,591 of 11,224 windows);
- accepted-window precision / within-5-bpm fraction: 89.64%;
- accepted-window pulse-rate MAE: 2.57 bpm;
- accepted-window RMSE: 5.73 bpm;
- AUROC: 0.844; AUPRC: 0.869;
- balanced accuracy: 0.730;
- Brier score: 0.160; 10-bin expected calibration error: 0.0229.

Across the three held-out participants, the accepted-window participant-macro MAE is 2.69 bpm and macro within-5-bpm fraction is 89.03%. Per-participant within-5-bpm fractions are 90.38% (S13), 90.61% (S6), and 86.09% (S8). The ungated participant-macro MAE is 17.54 bpm.

The 8-second windows use a 2-second stride and therefore overlap by 75%. Adjacent windows are serially correlated; window-level IID assumptions and naive bootstrap confidence intervals are invalid. Only three held-out participants are available, so no demographic, fairness, clinical or population-generalization claim is supported.

Decision: the gate substantially improves the usable subset and demonstrates correct abstention behavior, but it remains a research artifact. Test precision is 0.36 percentage points below the desired 90% level, coverage is limited, and activity-specific results vary sharply. The test set has now been observed and must not be reused to tune a claimed final model. Promotion requires a new external wearable/reference-sensor study, predefined subgroup/device/skin-tone/motion analysis and clinical/regulatory governance appropriate to the intended claim.

## Model artifact

`ml/models/ppg-quality-model.json` is a regenerated, non-executable, reviewable logistic-regression artifact with ten ordered features, imputer/scaler parameters, coefficients, intercept, threshold, exact dataset hashes, participant split and held-out metrics. It loads through dimension- and finite-value-validated inference code. It is explicitly labelled research-only and is not wired into the production health path.

## Claim boundary

- No disease dataset or disease classifier was trained, because Member 2 owns signal acquisition/quality/fusion rather than diagnosis.
- Dual-channel SpO2 feature extraction is implemented and validated on real paired optical signals. Numeric estimation deliberately abstains without verified wavelength mapping and a device-specific calibration validated against synchronized arterial/co-oximetry references; the available 94-99% boundary spot checks are insufficient.
- One Sleep-EDF pair validates conversion and bounds, not a general sleep-stage model.
- Real public data strengthens engineering evidence; it does not replace prospective clinical validation or real Android/OEM/wearable testing.
