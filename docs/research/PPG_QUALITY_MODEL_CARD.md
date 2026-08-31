# PPG Signal-Usability Model Card

## Model

`transparent-logistic-regression-v1` is a small, interpretable quality gate trained on PPG-DaLiA participants. It predicts whether the repository's baseline pulse-rate estimate is likely to be within 5 bpm of the ECG-derived reference for an 8-second window.

## Intended use

- Abstain or lower confidence when an input PPG window is unlikely to support this pulse-rate estimator.
- Supply quality metadata to Member 2 fusion and downstream explanation.
- Research and engineering validation only.

## Prohibited use

- Disease diagnosis, screening, treatment, triage or emergency detection.
- Estimating SpO2 from single-channel PPG/BVP.
- Claiming that a low-quality signal means the user is unhealthy.
- Applying the model to a new sensor/population without external validation and recalibration.

## Inputs and features

An 8-second PPG window, sampling rate, and optional aligned acceleration. The model receives spectral SNR/entropy, autocorrelation, peak-interval variation, shape statistics, flatline/saturation estimates, motion RMS and PPG-motion correlation. It does not receive participant identity, the ECG label, or a disease label.

## Training and evaluation

Participant-disjoint 60/20/20 train/validation/test split with a fixed seed. Imputation and scaling are fitted inside the training pipeline. The acceptance threshold is chosen on validation data only. The model is serialized as reviewed JSON coefficients/statistics rather than an executable pickle.

The generated artifact is `ml/models/ppg-quality-model.json`. It includes the exact input archive hash, participant split, quality-target definition, acceptance threshold and untouched test metrics. The schema-1.1 local report additionally records per-participant and participant-macro error summaries. Regenerating it requires the approved local dataset and benchmark command; the model artifact contains no raw signal or participant-level prediction.

## Known limitations

PPG-DaLiA contains 15 participants and a specific wrist device/protocol. Only three participants are held out for the final test. Its 8-second windows use a 2-second stride (75% overlap), so adjacent windows are serially correlated and naive window-level confidence intervals are invalid. A quality target based on this baseline's estimation error is algorithm-dependent. Performance may change with skin tone, perfusion, tattoos, fit, ambient light, exercise, arrhythmia, device wavelength/geometry or sampling configuration. The dataset is insufficient for a clinical or fairness claim; future evaluation must report relevant subgroup performance, participant-level uncertainty and abstention coverage.

Respiratory-rate baselines are evaluated separately on BIDMC against its two manual breath annotators. They are not inputs to this quality model and do not support respiratory-disease detection.
