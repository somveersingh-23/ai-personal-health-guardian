import pandas as pd

from ml.member1.preprocessing.preprocessing import clean_dataset, create_feature_dataset


def test_clean_and_feature_dataset():
    raw = pd.DataFrame([
        {"event_id": 1, "user_id": 1, "event_type": "heart_rate", "event_time": "2026-10-20T08:00:00Z", "value": 70, "unit": "bpm", "source": "test", "notes": ""},
        {"event_id": 2, "user_id": 1, "event_type": "heart_rate", "event_time": "2026-10-21T08:00:00Z", "value": 74, "unit": "bpm", "source": "test", "notes": ""},
        {"event_id": 3, "user_id": 1, "event_type": "heart_rate", "event_time": "2026-10-22T08:00:00Z", "value": 72, "unit": "bpm", "source": "test", "notes": ""},
    ])
    cleaned = clean_dataset(raw)
    features = create_feature_dataset(cleaned)
    assert len(features) == 3
    assert "rolling_mean_3" in features.columns
    assert "percentage_change" in features.columns
    assert features["event_time"].is_monotonic_increasing
