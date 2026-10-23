from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


class DigitalTwinStateEngine:
    """Build a per-user snapshot from event, baseline and anomaly tables."""

    @staticmethod
    def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
        clean = frame.copy()
        clean = clean.astype(object).where(pd.notna(clean), None)
        records = clean.to_dict(orient="records")
        for record in records:
            for key, value in list(record.items()):
                if hasattr(value, "isoformat"):
                    record[key] = value.isoformat()
                elif hasattr(value, "item"):
                    record[key] = value.item()
        return records

    @staticmethod
    def _value_map(latest: pd.DataFrame) -> dict[str, dict[str, Any]]:
        result = {}
        for _, row in latest.iterrows():
            metric = str(row["event_type"])
            result[metric] = {
                "value": float(row["value"]),
                "unit": str(row.get("unit") or ""),
                "timestamp": row["event_time"].isoformat(),
            }
        return result

    def build_state(
        self,
        events: pd.DataFrame,
        baselines: pd.DataFrame,
        anomalies: pd.DataFrame,
        user_id: int,
    ) -> dict[str, Any]:
        required = {"user_id", "event_type", "event_time", "value"}
        if not required.issubset(events.columns):
            raise ValueError(f"Events need columns: {sorted(required)}")

        user_events = events[events["user_id"].astype(int) == int(user_id)].copy()
        if user_events.empty:
            raise ValueError(f"No health events available for user {user_id}")

        user_events["event_time"] = pd.to_datetime(user_events["event_time"], errors="coerce", utc=True)
        user_events["value"] = pd.to_numeric(user_events["value"], errors="coerce")
        user_events = user_events.dropna(subset=["event_time", "value"])
        user_events = user_events.sort_values("event_time")
        latest = user_events.sort_values("event_time").groupby("event_type", as_index=False).tail(1)

        user_baselines = baselines[baselines["user_id"].astype(int) == int(user_id)].copy() if not baselines.empty else pd.DataFrame()
        user_anomalies = anomalies[anomalies["user_id"].astype(int) == int(user_id)].copy() if not anomalies.empty else pd.DataFrame()
        if not user_anomalies.empty and "is_anomaly" in user_anomalies:
            user_anomalies = user_anomalies[
                user_anomalies["is_anomaly"].astype(str).str.lower().isin(["true", "1"])
            ]

        high = int((user_anomalies.get("severity", pd.Series(dtype=str)) == "high").sum())
        moderate = int((user_anomalies.get("severity", pd.Series(dtype=str)) == "moderate").sum())
        low = int((user_anomalies.get("severity", pd.Series(dtype=str)) == "low").sum())
        anomaly_count = len(user_anomalies)

        if high >= 2:
            state = "attention_required"
        elif high >= 1 or moderate >= 3:
            state = "elevated"
        elif anomaly_count:
            state = "watch"
        else:
            state = "stable"

        anomaly_score = round(min(1.0, (high * 0.35 + moderate * 0.18 + low * 0.05)), 3)
        metric_map = self._value_map(latest)
        current_metrics = [
            {
                "type": str(row["event_type"]),
                "value": float(row["value"]),
                "unit": str(row.get("unit") or ""),
                "timestamp": row["event_time"].isoformat(),
            }
            for _, row in latest.sort_values("event_type").iterrows()
        ]

        baselines_records = self._records(user_baselines) if not user_baselines.empty else []
        anomalies_records = self._records(
            user_anomalies.sort_values("event_time", ascending=False).head(20)
        ) if not user_anomalies.empty else []
        recent_events = self._records(user_events.sort_values("event_time", ascending=False).head(20))

        baseline_lookup = {}
        if not user_baselines.empty:
            for _, row in user_baselines.iterrows():
                baseline_lookup[str(row["event_type"])] = {
                    "mean": float(row["mean"]),
                    "std": float(row.get("std", 0) or 0),
                    "lower_bound": float(row.get("lower_bound", row["mean"])),
                    "upper_bound": float(row.get("upper_bound", row["mean"])),
                    "unit": str(row.get("unit") or ""),
                }

        trends = []
        for metric, values in user_events.groupby("event_type"):
            values = values.sort_values("event_time")["value"].tail(7)
            if len(values) >= 2:
                first, last = float(values.iloc[0]), float(values.iloc[-1])
                pct = ((last - first) / abs(first) * 100) if first else 0.0
                direction = "stable" if abs(pct) < 5 else ("increasing" if pct > 0 else "decreasing")
                trends.append({
                    "metric_type": str(metric),
                    "direction": direction,
                    "change_percentage": round(pct, 2),
                    "period": f"last {len(values)} observations",
                })

        vitals = {key: metric_map[key] for key in (
            "heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic",
            "blood_glucose", "spo2", "weight"
        ) if key in metric_map}
        lifestyle = {key: metric_map[key] for key in (
            "sleep_duration", "steps", "calories", "water_intake"
        ) if key in metric_map}

        generated_at = datetime.now(timezone.utc).isoformat()
        latest_time = user_events["event_time"].max().isoformat()
        return {
            "user_id": int(user_id),
            "generated_at": generated_at,
            "latest_event_time": latest_time,
            "state": state,
            "anomaly_score": anomaly_score,
            "summary": {
                "total_events": int(len(user_events)),
                "total_anomalies": int(anomaly_count),
                "high_anomalies": high,
                "moderate_anomalies": moderate,
                "low_anomalies": low,
                "metrics_tracked": int(latest["event_type"].nunique()),
            },
            "current_metrics": current_metrics,
            "vitals": vitals,
            "lifestyle": lifestyle,
            "baselines": baselines_records,
            "baseline_lookup": baseline_lookup,
            "trends": trends,
            "anomalies": anomalies_records,
            "recent_events": recent_events,
        }

    def save_state(self, state: dict[str, Any], output_file: Path) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False, allow_nan=False)

    def save_metric_state_table(self, state: dict[str, Any], output_file: Path) -> None:
        rows = []
        baselines = {str(row.get("event_type")): row for row in state.get("baselines", [])}
        for metric in state.get("current_metrics", []):
            baseline = baselines.get(metric["type"], {})
            rows.append({
                "user_id": state["user_id"],
                "generated_at": state["generated_at"],
                "metric_type": metric["type"],
                "value": metric["value"],
                "unit": metric.get("unit", ""),
                "timestamp": metric.get("timestamp", ""),
                "baseline_mean": baseline.get("mean"),
                "baseline_lower_bound": baseline.get("lower_bound"),
                "baseline_upper_bound": baseline.get("upper_bound"),
                "state": state["state"],
            })
        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(output_file, index=False)
