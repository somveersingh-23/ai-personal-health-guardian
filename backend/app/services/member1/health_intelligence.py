import csv
import json
from pathlib import Path
from typing import Any


class HealthIntelligenceService:
    """Read outputs produced by the Member 1 ML pipeline.

    The API deliberately does not run ML training/inference inside a request.
    Run the ML scripts first; missing artifacts are reported as 404.
    """

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path(__file__).resolve().parents[4]
        self.processed_dir = self.project_root / "ml" / "member1" / "data" / "processed"
        self.twin_dir = self.processed_dir / "digital_twin"
        self.insights_dir = self.processed_dir / "insights"

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(f"ML artifact not found: {path.name}. Run the ML pipeline first.")
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"ML artifact is unreadable: {path.name}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"ML artifact must contain a JSON object: {path.name}")
        return data

    def get_digital_twin(self, user_id: int) -> dict[str, Any]:
        if user_id <= 0:
            raise ValueError("user_id must be positive")
        return self._read_json(self.twin_dir / f"user_{user_id}_state.json")

    def get_digital_twin_metrics(self, user_id: int) -> list[dict[str, Any]]:
        if user_id <= 0:
            raise ValueError("user_id must be positive")
        path = self.twin_dir / f"user_{user_id}_metrics.csv"
        if not path.is_file():
            raise FileNotFoundError(f"ML artifact not found: {path.name}. Run the ML pipeline first.")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def get_insights(self, user_id: int) -> dict[str, Any]:
        if user_id <= 0:
            raise ValueError("user_id must be positive")
        per_user = self.insights_dir / f"user_{user_id}_insights.json"
        if per_user.is_file():
            return self._read_json(per_user)

        global_file = self.insights_dir / "personalized_insights.json"
        global_data = self._read_json(global_file)
        all_insights = global_data.get("insights", [])
        user_insights = [
            item for item in all_insights
            if isinstance(item, dict) and str(item.get("user_id")) == str(user_id)
        ]
        if not user_insights:
            raise FileNotFoundError(f"No insights found for user {user_id}. Run the insights pipeline.")
        return {
            "user_id": user_id,
            "generated_at": global_data.get("generated_at", ""),
            "digital_twin_state": "no_data",
            "anomaly_score": 0.0,
            "insight_count": len(user_insights),
            "insights": [
                {key: value for key, value in item.items() if key != "user_id"}
                for item in user_insights
            ],
        }

    def get_health_intelligence(self, user_id: int) -> dict[str, Any]:
        twin = self.get_digital_twin(user_id)
        insights = self.get_insights(user_id)
        return {
            "user_id": user_id,
            "generated_at": twin.get("generated_at"),
            "state": twin.get("state", "no_data"),
            "anomaly_score": twin.get("anomaly_score", 0.0),
            "summary": twin.get("summary", {}),
            "current_metrics": twin.get("current_metrics", []),
            "insight_count": insights.get("insight_count", 0),
            "insights": insights.get("insights", []),
        }
