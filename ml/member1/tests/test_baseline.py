import pandas as pd

from ml.member1.baseline.baseline_engine import PersonalBaselineEngine


def test_personal_baseline_computes_per_user_metric():
    rows = []
    for i in range(12):
        rows.append({
            "user_id": 1,
            "event_type": "heart_rate",
            "event_time": f"2026-10-{i+1:02d}T08:00:00Z",
            "value": 70 + (i % 3),
        })
    result = PersonalBaselineEngine(minimum_observations=10).calculate_baselines(pd.DataFrame(rows))
    assert len(result) == 1
    assert result.iloc[0]["observation_count"] == 12
    assert result.iloc[0]["lower_bound"] <= result.iloc[0]["upper_bound"]
