import pandas as pd

from ml.member1.anomaly_detection.anomaly_engine import AnomalyDetectionEngine


def test_anomaly_engine_flags_large_deviation():
    events = pd.DataFrame([
        {"event_id": 1, "user_id": 1, "event_type": "heart_rate", "event_time": "2026-10-20T08:00:00Z", "value": 72, "unit": "bpm"},
        {"event_id": 2, "user_id": 1, "event_type": "heart_rate", "event_time": "2026-10-21T08:00:00Z", "value": 120, "unit": "bpm"},
    ])
    baselines = pd.DataFrame([{
        "user_id": 1, "event_type": "heart_rate", "mean": 72,
        "std": 4, "lower_bound": 64, "upper_bound": 80,
    }])
    scored = AnomalyDetectionEngine().detect(events, baselines)
    assert bool(scored.loc[scored["event_id"] == 2, "is_anomaly"].iloc[0])
    assert scored.loc[scored["event_id"] == 2, "severity"].iloc[0] == "high"
