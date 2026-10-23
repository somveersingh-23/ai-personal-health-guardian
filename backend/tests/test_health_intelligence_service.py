import json

from app.services.member1.health_intelligence import HealthIntelligenceService


def test_reads_per_user_twin_and_insights(tmp_path):
    processed = tmp_path / "ml" / "member1" / "data" / "processed"
    twin_dir = processed / "digital_twin"
    insights_dir = processed / "insights"
    twin_dir.mkdir(parents=True)
    insights_dir.mkdir(parents=True)

    (twin_dir / "user_7_state.json").write_text(json.dumps({
        "user_id": 7,
        "generated_at": "2026-10-23T10:00:00+00:00",
        "state": "stable",
        "anomaly_score": 0.0,
        "summary": {"total_events": 10},
        "current_metrics": [],
    }), encoding="utf-8")
    (insights_dir / "user_7_insights.json").write_text(json.dumps({
        "user_id": 7,
        "generated_at": "2026-10-23T10:00:00+00:00",
        "digital_twin_state": "stable",
        "anomaly_score": 0.0,
        "insight_count": 0,
        "insights": [],
    }), encoding="utf-8")

    service = HealthIntelligenceService(project_root=tmp_path)
    assert service.get_digital_twin(7)["state"] == "stable"
    assert service.get_insights(7)["insight_count"] == 0
    assert service.get_health_intelligence(7)["summary"]["total_events"] == 10
