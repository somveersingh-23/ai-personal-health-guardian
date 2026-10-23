import pandas as pd

from ml.member1.digital_twin.state_engine import DigitalTwinStateEngine


def test_twin_builds_user_state():
    events = pd.DataFrame([
        {"event_id": 1, "user_id": 1, "event_type": "heart_rate", "event_time": "2026-10-20T08:00:00Z", "value": 72, "unit": "bpm"},
        {"event_id": 2, "user_id": 1, "event_type": "sleep_duration", "event_time": "2026-10-21T08:00:00Z", "value": 7.5, "unit": "hours"},
    ])
    baselines = pd.DataFrame([
        {"user_id": 1, "event_type": "heart_rate", "mean": 72, "std": 3, "lower_bound": 65, "upper_bound": 79},
    ])
    anomalies = pd.DataFrame([
        {"event_id": 1, "user_id": 1, "event_type": "heart_rate", "event_time": "2026-10-20T08:00:00Z", "value": 72, "is_anomaly": False, "severity": "low"},
    ])
    state = DigitalTwinStateEngine().build_state(events, baselines, anomalies, 1)
    assert state["user_id"] == 1
    assert state["state"] == "stable"
    assert len(state["current_metrics"]) == 2
    assert "heart_rate" in state["vitals"]
