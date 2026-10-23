"""Create reproducible, non-clinical synthetic health-event data for development."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

MEMBER1_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = MEMBER1_DIR / "data" / "raw"
NORMAL_FILE = RAW_DIR / "synthetic_health_events.csv"
ANOMALY_FILE = RAW_DIR / "synthetic_health_events_with_anomalies.csv"

METRICS = {
    "heart_rate": ("bpm", 70.0, 4.0),
    "blood_pressure_systolic": ("mmHg", 118.0, 5.0),
    "blood_pressure_diastolic": ("mmHg", 77.0, 3.5),
    "blood_glucose": ("mg/dL", 95.0, 5.0),
    "spo2": ("percent", 98.0, 0.5),
    "sleep_duration": ("hours", 7.3, 0.45),
    "steps": ("steps", 7200.0, 850.0),
    "calories": ("kcal", 2100.0, 160.0),
    "water_intake": ("liters", 2.1, 0.25),
    "weight": ("kg", 68.0, 0.25),
}


def generate(seed: int = 20261023, days: int = 30, users: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    now = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    rows: list[dict] = []
    event_id = 1

    for user_id in range(1, users + 1):
        user_shift = (user_id - 2) * 0.8
        for day in range(days):
            date = now - timedelta(days=days - day - 1)
            for metric, (unit, mean, std) in METRICS.items():
                # A consistent user-specific baseline with modest daily variation.
                value = float(rng.normal(mean + user_shift, std))
                if metric in {"steps", "calories"}:
                    value = max(0.0, value)
                if metric in {"sleep_duration", "water_intake", "weight"}:
                    value = max(0.1, value)
                rows.append({
                    "event_id": event_id,
                    "user_id": user_id,
                    "event_type": metric,
                    "event_time": (date + timedelta(minutes=day % 4 * 13)).isoformat(),
                    "value": round(value, 2),
                    "unit": unit,
                    "source": "synthetic",
                    "notes": "Synthetic development data; not a real patient record.",
                })
                event_id += 1

    normal = pd.DataFrame(rows)
    with_anomalies = normal.copy()
    # Inject known deviations for testability. They are intentionally synthetic.
    injected = [
        (1, "heart_rate", 24, 112.0),
        (1, "sleep_duration", 25, 3.2),
        (2, "steps", 26, 900.0),
        (2, "blood_pressure_systolic", 27, 158.0),
        (3, "water_intake", 28, 0.5),
        (3, "spo2", 29, 91.0),
    ]
    for user_id, metric, day, value in injected:
        mask = (
            (with_anomalies["user_id"] == user_id)
            & (with_anomalies["event_type"] == metric)
            & (with_anomalies["event_time"].str.startswith(
                (now - timedelta(days=days - day - 1)).date().isoformat()
            ))
        )
        indices = with_anomalies.index[mask]
        if len(indices):
            with_anomalies.loc[indices[-1], "value"] = value
            with_anomalies.loc[indices[-1], "notes"] = "Injected synthetic deviation for pipeline validation."

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    normal.to_csv(NORMAL_FILE, index=False)
    with_anomalies.to_csv(ANOMALY_FILE, index=False)
    return normal, with_anomalies


if __name__ == "__main__":
    normal, anomaly = generate()
    print(f"Wrote {len(normal)} normal rows and {len(anomaly)} anomaly-test rows.")
    print(f"Normal: {NORMAL_FILE}")
    print(f"With injected deviations: {ANOMALY_FILE}")
