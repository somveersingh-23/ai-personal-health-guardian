# Member 2 Real-Data Validation Protocol

## Objective

Establish whether the Member 2 pipeline can ingest authoritative research signals, preserve provenance, identify unusable PPG windows, and pass trustworthy aggregate evidence to Members 1 and 3. The protocol evaluates signal handling; it does not evaluate disease diagnosis.

## Predefined design

1. Use the official PPG-DaLiA alignment: 8-second windows with a 2-second stride.
2. Split by participant with a fixed seed into 60% train, 20% validation and 20% untouched test. A participant can appear in exactly one set.
3. Estimate pulse rate using a transparent 0.5–3.67 Hz band-limited spectral baseline. Use simultaneous accelerometry to penalize motion-correlated spectral energy.
4. Extract auditable features: spectral SNR/entropy, autocorrelation, beat-interval variation, skewness, kurtosis, flatline/saturation fractions, acceleration RMS and PPG-motion correlation.
5. Define an engineering usability target as absolute baseline error at or below 5 bpm. This target describes whether this estimator's window is usable; it is not a clinical normal/abnormal threshold.
6. Fit only a median-imputed, standardized, class-balanced logistic quality gate on training participants.
7. Select the acceptance threshold on validation participants, preferring at least 90% accepted-window precision and then maximum coverage. The test set remains untouched until final reporting.
8. Report all-window and accepted-window MAE, RMSE, median/p95 absolute error, fraction within 5 bpm, Bland–Altman bias/limits, acceptance coverage, accepted precision, recall, balanced accuracy, AUROC and AUPRC where defined.
9. Run the untuned baseline on held-out BIDMC participants as a separate domain sanity check. Never combine it with PPG-DaLiA as if the sensors/populations were interchangeable.
10. On the same held-out BIDMC participants, compare frozen PPG baseline/amplitude/frequency fusion and impedance-respiration estimates with both human breath annotators using 64-second windows and 8-second stride. Report component agreement as a diagnostic, never as an assumed quality gate.
11. Evaluate that frozen PPG respiratory-rate method on all 42 CapnoBase cases using 64-second windows and 8-second stride. CapnoBase is benchmark-only: never train, tune, or select thresholds on it.
12. Validate paired optical-channel feature extraction on the 22-participant, 66-record PhysioNet PTT-PPG dataset using non-overlapping 8-second windows at distal and proximal sensors. Record the publisher's internally conflicting red/infrared channel mapping and keep ratio orientation wavelength-neutral. Do not fit SpO2 calibration from its unsynchronized boundary spot checks; verify explicit abstention instead.
13. Validate the curated Sleep-EDF expert annotations and all real reference events against the exact production `ReadingCreate` contract.

## Reproducible commands

```powershell
$env:PYTHONPATH = "ml;backend"
$env:HEALTH_GUARDIAN_DATA_ROOT = "D:\AIHealthData" # optional external data drive
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli prepare ppg-dalia
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli validate-contracts bidmc
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli benchmark bidmc
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli validate-contracts ppg-dalia
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli benchmark ppg-dalia
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli download capnobase --accept-dataset-terms
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli benchmark capnobase
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli download ptt-ppg
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli benchmark ptt-ppg
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli validate-contracts sleep-edf
```

Local reports and the transparent logistic-regression parameters are written to `ml/reports/local/`, which is Git-ignored. Review an aggregate report before copying a redacted summary into project documentation.

## Release gates

- Dataset hashes, licences and versions are recorded and re-verifiable.
- Unit/security/contract tests and full real-data runs pass.
- Train/validation/test participant sets have zero overlap.
- Failures and abstentions remain visible; no missing window is silently converted to a measurement.
- Results are stated for their exact device, population and protocol. No medical accuracy or disease claim is made.
- A future product claim requires prospective reference-device testing, predefined subgroup analysis (including device/skin-tone/motion conditions where relevant), clinical governance, and applicable regulatory review.
