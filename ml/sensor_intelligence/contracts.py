"""Builders for offline research readings compatible with the backend contract."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5


def _identity(dataset: str, participant: str, record_type: str, record_id: str) -> dict[str, Any]:
    stable_name = f"health-guardian:{dataset}:{participant}:{record_type}:{record_id}"
    return {
        "schema_version": "2.0.0",
        "event_id": str(uuid5(NAMESPACE_URL, stable_name)),
        "source": "research_dataset",
        "data_origin_package": f"research.{dataset}",
        "source_record_type": record_type,
        "source_record_id": record_id,
        "device_id": f"{dataset}:{participant}",
        "device_manufacturer": "research-dataset",
        "device_model": dataset,
        "device_type": "research_reference",
        "recording_method": "automatically_recorded",
        "permission_state": "unavailable",
    }


def instant_reading(
    *,
    dataset: str,
    participant: str,
    record_type: str,
    record_id: str,
    metric: str,
    unit: str,
    observed_at: datetime,
    value: float,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **_identity(dataset, participant, record_type, record_id),
        "temporal_type": "instant",
        "metric": metric,
        "unit": unit,
        "observed_at": observed_at.astimezone(UTC).isoformat(),
        "value": float(value),
        "metadata": metadata or {},
    }


def series_reading(
    *,
    dataset: str,
    participant: str,
    record_type: str,
    record_id: str,
    metric: str,
    unit: str,
    start_at: datetime,
    times_seconds: list[float],
    values: list[float],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not values or len(times_seconds) != len(values):
        raise ValueError("series times and values must be non-empty and aligned")
    samples = [
        {
            "observed_at": datetime.fromtimestamp(
                start_at.timestamp() + float(offset),
                tz=UTC,
            ).isoformat(),
            "value": float(value),
        }
        for offset, value in zip(times_seconds, values, strict=True)
    ]
    return {
        **_identity(dataset, participant, record_type, record_id),
        "temporal_type": "series",
        "metric": metric,
        "unit": unit,
        "start_at": samples[0]["observed_at"],
        "end_at": samples[-1]["observed_at"],
        "samples": samples,
        "metadata": metadata or {},
    }


def sleep_session_reading(
    *,
    dataset: str,
    participant: str,
    record_id: str,
    start_at: datetime,
    end_at: datetime,
    stages: list[dict[str, str]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **_identity(dataset, participant, "ExpertScoredSleepSession", record_id),
        "temporal_type": "session",
        "metric": "sleep_duration",
        "unit": "min",
        "start_at": start_at.astimezone(UTC).isoformat(),
        "end_at": end_at.astimezone(UTC).isoformat(),
        "stages": stages,
        "metadata": metadata or {},
    }
