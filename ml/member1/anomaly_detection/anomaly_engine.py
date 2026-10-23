from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    ANOMALY_OUTPUT_FILE,
    BASELINE_FILE,
    HIGH_Z_SCORE,
    INPUT_DATASET,
    MIN_ABSOLUTE_Z_SCORE,
)


class AnomalyDetectionEngine:
    """Compare observations with a user's learned statistical baseline."""

    REQUIRED_EVENT_COLUMNS = {"event_id", "user_id", "event_type", "event_time", "value"}
    REQUIRED_BASELINE_COLUMNS = {"user_id", "event_type", "mean", "std", "lower_bound", "upper_bound"}

    @staticmethod
    def _validate(df: pd.DataFrame, required: set[str], label: str) -> None:
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")

    def detect(self, events: pd.DataFrame, baselines: pd.DataFrame) -> pd.DataFrame:
        self._validate(events, self.REQUIRED_EVENT_COLUMNS, "events")
        self._validate(baselines, self.REQUIRED_BASELINE_COLUMNS, "baselines")

        data = events.copy()
        data["user_id"] = pd.to_numeric(data["user_id"], errors="coerce")
        data["value"] = pd.to_numeric(data["value"], errors="coerce")
        data["event_time"] = pd.to_datetime(data["event_time"], errors="coerce", utc=True)
        data = data.dropna(subset=["user_id", "value", "event_time", "event_type"])
        data["user_id"] = data["user_id"].astype(int)

        base = baselines.copy()
        base["user_id"] = pd.to_numeric(base["user_id"], errors="coerce")
        for col in ("mean", "std", "lower_bound", "upper_bound"):
            base[col] = pd.to_numeric(base[col], errors="coerce")
        base = base.dropna(subset=["user_id", "event_type", "mean", "std"])
        base["user_id"] = base["user_id"].astype(int)

        merged = data.merge(
            base,
            on=["user_id", "event_type"],
            how="left",
            suffixes=("", "_baseline"),
        )
        merged["std_safe"] = merged["std"].fillna(0).clip(lower=0.000001)
        merged["z_score"] = (merged["value"] - merged["mean"]) / merged["std_safe"]
        merged["deviation_score"] = merged["z_score"].abs()
        outside_percentiles = (
            (merged["lower_bound"].notna() & (merged["value"] < merged["lower_bound"]))
            | (merged["upper_bound"].notna() & (merged["value"] > merged["upper_bound"]))
        )
        merged["is_anomaly"] = (
            (merged["deviation_score"] >= MIN_ABSOLUTE_Z_SCORE)
            | (outside_percentiles & (merged["deviation_score"] >= 1.8))
        )
        merged["severity"] = np.select(
            [
                merged["is_anomaly"] & (merged["deviation_score"] >= HIGH_Z_SCORE),
                merged["is_anomaly"] & (merged["deviation_score"] >= MIN_ABSOLUTE_Z_SCORE),
            ],
            ["high", "moderate"],
            default="low",
        )
        merged["confidence"] = np.where(
            merged["is_anomaly"],
            (0.5 + (merged["deviation_score"].clip(0, 5) / 10)).clip(0.5, 0.99),
            0.0,
        )
        merged["explanation"] = np.where(
            merged["is_anomaly"],
            "Observed value differs from this user's learned historical distribution; verify the measurement and context.",
            "No deviation crossed the configured statistical threshold.",
        )
        return merged.drop(columns=["std_safe"])

    def run(
        self,
        input_file: Path = INPUT_DATASET,
        baseline_file: Path = BASELINE_FILE,
        output_file: Path = ANOMALY_OUTPUT_FILE,
    ) -> pd.DataFrame:
        if not input_file.is_file():
            raise FileNotFoundError(f"Processed event dataset not found: {input_file}")
        if not baseline_file.is_file():
            raise FileNotFoundError(f"Baseline file not found: {baseline_file}")
        events = pd.read_csv(input_file)
        baselines = pd.read_csv(baseline_file)
        scored = self.detect(events, baselines)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        scored.to_csv(output_file, index=False)
        return scored


def main() -> None:
    result = AnomalyDetectionEngine().run()
    print(f"Scored {len(result)} events; flagged {int(result['is_anomaly'].sum())} deviations.")


if __name__ == "__main__":
    main()
