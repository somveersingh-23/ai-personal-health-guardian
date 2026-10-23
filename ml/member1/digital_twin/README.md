# Personal Health Digital Twin

The state engine combines the processed synthetic health-event table, personal baselines,
and scored anomaly table. It writes one JSON state and one current-metric CSV per user.

Run from the repository root in this order:
1. `python -m ml.member1.data.generate_synthetic_health_data`
2. `python -m ml.member1.preprocessing.run_preprocessing`
3. `python -m ml.member1.baseline.run_baseline`
4. `python -m ml.member1.anomaly_detection.anomaly_engine`
5. `python -m ml.member1.digital_twin.run_digital_twin`
6. `python -m ml.member1.inshights.run_insights`

The output is synthetic development data and is not a clinical assessment.
