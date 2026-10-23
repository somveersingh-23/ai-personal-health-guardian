from ml.member1.inshights.inshights_engine import PersonalizedInsightEngine


def test_insight_engine_generates_state_and_lifestyle_insights():
    twin = {
        "user_id": 1,
        "state": "stable",
        "anomaly_score": 0.0,
        "anomalies": [],
        "lifestyle": {
            "sleep_duration": {"value": 5.0, "unit": "hours"},
            "steps": {"value": 2000, "unit": "steps"},
        },
    }
    insights = PersonalizedInsightEngine().generate_insights(twin)
    assert insights
    assert any(item["category"] == "sleep" for item in insights)
    assert all("recommended_action" in item for item in insights)
