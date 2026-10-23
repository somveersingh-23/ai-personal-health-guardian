# Member 1 ML Pipeline

Run from the repository root:

```bash
python scripts/run_member1_ml_pipeline.py
```

## Stages
1. `ml/member1/data/generate_synthetic_health_data.py` creates normal and injected-deviation synthetic data.
2. `ml/member1/preprocessing/preprocessing.py` validates, cleans, sorts, and creates time, rolling, and change features.
3. `ml/member1/baseline/baseline_engine.py` calculates per-user/per-metric summary statistics and percentile bounds from the normal dataset.
4. `ml/member1/anomaly_detection/anomaly_engine.py` compares the deviation-test events to learned baselines and emits anomaly flag, z-score, severity, confidence, and explanation.
5. `ml/member1/digital_twin/state_engine.py` aggregates current metrics, baseline comparisons, trends, anomaly counts, and state for each user.
6. `ml/member1/inshights/inshights_engine.py` produces bounded, data-driven observation/action text from the twin and anomalies.

## Main outputs
- `ml/member1/data/processed/normal/processed_health_events.csv`
- `ml/member1/data/processed/anomalies/processed_health_events.csv`
- `ml/member1/data/processed/baselines/personal_baselines.csv`
- `ml/member1/data/processed/anomalies/detected_anomalies.csv`
- `ml/member1/data/processed/digital_twin/user_<id>_state.json`
- `ml/member1/data/processed/digital_twin/user_<id>_metrics.csv`
- `ml/member1/data/processed/insights/user_<id>_insights.json`
- `ml/member1/data/processed/insights/personalized_insights.json` and `.csv`

The statistical thresholds are engineering defaults for a student prototype, not medical thresholds. Synthetic data is not patient data. Verify units and sensor data quality before using real measurements.
