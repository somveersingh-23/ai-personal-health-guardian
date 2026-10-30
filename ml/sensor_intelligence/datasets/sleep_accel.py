"""Apple Watch Sleep-Accel adapter with PSG-labelled session conversion.

Raw Apple Watch acceleration remains in the research-only data root.  The
production-contract adapter exposes only heart-rate samples and PSG-labelled
sleep sessions, both marked as dataset-relative research evidence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from sensor_intelligence.contracts import series_reading, sleep_session_reading

RESEARCH_ANCHOR = datetime(2020, 1, 1, tzinfo=UTC)
STAGE_NAMES = {0: "awake", 1: "light", 2: "light", 3: "deep", 5: "rem"}


@dataclass(frozen=True, slots=True)
class SleepAccelRecord:
    participant_id: str
    heart_rate_times_seconds: NDArray[np.float64]
    heart_rate_bpm: NDArray[np.float64]
    acceleration_times_seconds: NDArray[np.float64]
    acceleration_g: NDArray[np.float64]
    step_times_seconds: NDArray[np.float64]
    step_counts: NDArray[np.float64]
    sleep_label_times_seconds: NDArray[np.float64]
    sleep_labels: NDArray[np.int64]


def _table(path: Path, columns: int) -> NDArray[np.float64]:
    try:
        values = np.loadtxt(path, dtype=np.float64, ndmin=2)
    except ValueError as exc:
        raise ValueError(f"unable to parse {path.name}") from exc
    if values.ndim != 2 or values.shape[1] != columns or not np.isfinite(values).all():
        raise ValueError(f"{path.name} must contain {columns} finite columns")
    if values.shape[0] == 0:
        raise ValueError(f"{path.name} is empty")
    return values


def _strictly_increasing(values: NDArray[np.float64], name: str) -> None:
    if np.any(np.diff(values) <= 0):
        raise ValueError(f"{name} timestamps must be strictly increasing")


def _find(root: Path, participant_id: str, suffix: str) -> Path:
    candidates = sorted(root.rglob(f"{participant_id}_{suffix}.txt"))
    if len(candidates) != 1:
        raise FileNotFoundError(f"expected one {suffix} file for {participant_id}")
    return candidates[0]


def participant_ids(dataset_root: Path) -> list[str]:
    suffix = "_labeled_sleep.txt"
    identifiers = sorted(
        {path.name.removesuffix(suffix) for path in dataset_root.rglob(f"*{suffix}")}
    )
    if not identifiers:
        raise FileNotFoundError(f"no Sleep-Accel label files found below {dataset_root}")
    return identifiers


def load_record(dataset_root: Path, participant_id: str) -> SleepAccelRecord:
    heart_rate = _table(_find(dataset_root, participant_id, "heartrate"), 2)
    acceleration = _table(_find(dataset_root, participant_id, "acceleration"), 4)
    steps = _table(_find(dataset_root, participant_id, "steps"), 2)
    labels = _table(_find(dataset_root, participant_id, "labeled_sleep"), 2)
    for values, name in (
        (heart_rate[:, 0], "heart-rate"),
        (acceleration[:, 0], "acceleration"),
        (steps[:, 0], "steps"),
        (labels[:, 0], "sleep-label"),
    ):
        _strictly_increasing(values, name)
    integer_labels = labels[:, 1].astype(np.int64)
    labels_are_integral = np.array_equal(labels[:, 1], integer_labels)
    if not labels_are_integral or not set(integer_labels).issubset(STAGE_NAMES):
        raise ValueError("Sleep-Accel contains an unsupported sleep-stage label")
    return SleepAccelRecord(
        participant_id=participant_id,
        heart_rate_times_seconds=heart_rate[:, 0],
        heart_rate_bpm=heart_rate[:, 1],
        acceleration_times_seconds=acceleration[:, 0],
        acceleration_g=acceleration[:, 1:],
        step_times_seconds=steps[:, 0],
        step_counts=steps[:, 1],
        sleep_label_times_seconds=labels[:, 0],
        sleep_labels=integer_labels,
    )


def _anchor(participant_id: str) -> datetime:
    digest = hashlib.sha256(participant_id.encode("utf-8")).digest()
    return RESEARCH_ANCHOR + timedelta(days=int.from_bytes(digest[:2], "big") % 365)


def _stage_intervals(record: SleepAccelRecord, anchor: datetime) -> list[dict[str, str]]:
    times = record.sleep_label_times_seconds
    durations = np.diff(times)
    fallback = float(np.median(durations)) if durations.size else 30.0
    stages: list[dict[str, str]] = []
    for index, label in enumerate(record.sleep_labels):
        start = float(times[index])
        end = float(times[index + 1]) if index + 1 < times.size else start + fallback
        stages.append(
            {
                "start_at": (anchor + timedelta(seconds=start)).isoformat(),
                "end_at": (anchor + timedelta(seconds=end)).isoformat(),
                "stage": STAGE_NAMES[int(label)],
            }
        )
    return stages


def to_health_events(record: SleepAccelRecord) -> list[dict[str, object]]:
    valid_hr = (record.heart_rate_bpm >= 1.0) & (record.heart_rate_bpm <= 300.0)
    if not valid_hr.any():
        raise ValueError("Sleep-Accel has no valid heart-rate samples")
    anchor = _anchor(record.participant_id)
    stages = _stage_intervals(record, anchor)
    heart_rate_event = series_reading(
        dataset="sleep-accel",
        participant=record.participant_id,
        record_type="AppleWatchPPGDerivedHeartRate",
        record_id=f"sleep-accel-{record.participant_id}-heart-rate",
        metric="heart_rate",
        unit="bpm",
        start_at=anchor,
        times_seconds=record.heart_rate_times_seconds[valid_hr].tolist(),
        values=record.heart_rate_bpm[valid_hr].tolist(),
        metadata={
            "dataset_version": "1.0.0",
            "time_basis": "relative_anchored_not_clinical",
            "source_device": "apple_watch",
            "dropped_out_of_range_hr_samples": int((~valid_hr).sum()),
        },
    )
    sleep_event = sleep_session_reading(
        dataset="sleep-accel",
        participant=record.participant_id,
        record_id=f"sleep-accel-{record.participant_id}-psg-session",
        start_at=anchor + timedelta(seconds=float(record.sleep_label_times_seconds[0])),
        end_at=datetime.fromisoformat(stages[-1]["end_at"]),
        stages=stages,
        metadata={
            "dataset_version": "1.0.0",
            "time_basis": "relative_anchored_not_clinical",
            "sleep_reference": "polysomnography_label",
            "source_device": "apple_watch",
            "motion_samples": int(record.acceleration_g.shape[0]),
            "step_bins": int(record.step_counts.size),
        },
    )
    return [heart_rate_event, sleep_event]


__all__ = ["SleepAccelRecord", "load_record", "participant_ids", "to_health_events"]
