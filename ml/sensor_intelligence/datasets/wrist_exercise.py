"""WFDB adapter for the open Wrist PPG During Exercise dataset."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import wfdb

from sensor_intelligence.contracts import series_reading
from sensor_intelligence.datasets.records import EventAnnotation, ResearchRecord, SignalChannel

RESEARCH_ANCHOR = datetime(2020, 1, 1, tzinfo=UTC)


def _signal_indices(names: list[str], tokens: tuple[str, ...]) -> list[int]:
    return [
        index
        for index, name in enumerate(names)
        if any(token in name.lower() for token in tokens)
    ]


def _acceleration_indices(names: list[str]) -> tuple[list[int], str]:
    """Choose one physical tri-axial accelerometer, never combine two sensors."""

    normalized = [name.lower() for name in names]
    for sensor in (
        "wrist_low_noise_accelerometer",
        "wrist_wide_range_accelerometer",
    ):
        expected = [f"{sensor}_{axis}" for axis in ("x", "y", "z")]
        if all(channel in normalized for channel in expected):
            return [normalized.index(channel) for channel in expected], sensor
    indices = _signal_indices(names, ("acc", "acceler"))
    return indices, "generic_acceleration"


def _common_valid_length(samples: np.ndarray) -> int:
    """Return the shared finite prefix; reject any interior acquisition gap."""

    complete = np.isfinite(samples).all(axis=1)
    if not complete.any():
        raise ValueError("Wrist Exercise record contains no complete PPG/motion samples")
    first_missing = np.flatnonzero(~complete)
    if not first_missing.size:
        return int(complete.size)
    prefix_end = int(first_missing[0])
    if complete[prefix_end:].any():
        raise ValueError("Wrist Exercise record has an interior PPG/motion acquisition gap")
    if prefix_end == 0:
        raise ValueError("Wrist Exercise record begins with missing PPG/motion samples")
    return prefix_end


def participant_ids(dataset_root: Path) -> list[str]:
    records = sorted(path.with_suffix("").name for path in dataset_root.rglob("*.hea"))
    if not records:
        raise FileNotFoundError(f"no Wrist Exercise WFDB headers found below {dataset_root}")
    return records


def _record_path(dataset_root: Path, record_id: str) -> Path:
    candidates = sorted(dataset_root.rglob(f"{record_id}.hea"))
    if len(candidates) != 1:
        raise FileNotFoundError(f"expected one Wrist Exercise header for {record_id}")
    return candidates[0].with_suffix("")


def _anchor(record_id: str) -> datetime:
    digest = hashlib.sha256(record_id.encode("utf-8")).digest()
    return RESEARCH_ANCHOR + timedelta(days=int.from_bytes(digest[:2], "big") % 365)


def load_record(dataset_root: Path, record_id: str) -> ResearchRecord:
    path = _record_path(dataset_root, record_id)
    raw = wfdb.rdrecord(str(path))
    values = np.asarray(raw.p_signal, dtype=np.float64)
    names = list(raw.sig_name)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] != len(names):
        raise ValueError(f"Wrist Exercise record {record_id} has an invalid signal matrix")
    ppg_indices = _signal_indices(names, ("ppg", "pleth"))
    acceleration_indices, motion_sensor = _acceleration_indices(names)
    if len(ppg_indices) != 1 or not acceleration_indices:
        raise ValueError(
            f"Wrist Exercise record {record_id} lacks a unique PPG or acceleration signal"
        )
    sampling_rate = float(raw.fs)
    if sampling_rate <= 0:
        raise ValueError(f"Wrist Exercise record {record_id} has an invalid sample rate")
    retained_samples = _common_valid_length(
        values[:, [ppg_indices[0], *acceleration_indices]]
    )
    ppg = values[:retained_samples, ppg_indices[0]]
    acceleration = np.linalg.norm(
        values[:retained_samples, acceleration_indices], axis=1
    )
    peaks = np.asarray(wfdb.rdann(str(path), "atr").sample, dtype=np.int64)
    discarded_reference_peaks = int(np.sum(peaks >= retained_samples))
    peaks = peaks[peaks < retained_samples]
    annotation = EventAnnotation("ecg_r_peaks", peaks, sampling_rate)
    participant = record_id.split("_", maxsplit=1)[0]
    activity = record_id.removeprefix(f"{participant}_")
    return ResearchRecord(
        dataset="wrist-exercise",
        participant_id=record_id,
        duration_seconds=retained_samples / sampling_rate,
        channels={
            "ppg": SignalChannel("ppg", ppg, sampling_rate, "arbitrary_ppg_units"),
            "acceleration_magnitude": SignalChannel(
                "acceleration_magnitude",
                acceleration,
                sampling_rate,
                "arbitrary_imu_units",
            ),
        },
        annotations={"ecg_r_peaks": annotation},
        metadata={
            "participant": participant,
            "activity": activity,
            "acceleration_channels": len(acceleration_indices),
            "motion_sensor": motion_sensor,
            "discarded_trailing_ppg_motion_samples": values.shape[0] - retained_samples,
            "discarded_trailing_ecg_reference_peaks": discarded_reference_peaks,
            "missing_data_policy": (
                "trailing incomplete PPG/motion samples are excluded; no imputation"
            ),
        },
    )


def to_health_events(record: ResearchRecord) -> list[dict[str, object]]:
    peaks = record.annotations["ecg_r_peaks"].sample_indices
    intervals = np.diff(peaks) / record.annotations["ecg_r_peaks"].sampling_rate_hz
    heart_rate = 60.0 / intervals
    times = peaks[1:] / record.annotations["ecg_r_peaks"].sampling_rate_hz
    valid = np.isfinite(heart_rate) & (heart_rate >= 1.0) & (heart_rate <= 300.0)
    if not valid.any():
        raise ValueError("Wrist Exercise record has no physiologically bounded reference HR")
    return [
        series_reading(
            dataset="wrist-exercise",
            participant=record.participant_id,
            record_type="ChestECGRPeakDerivedHeartRate",
            record_id=f"wrist-exercise-{record.participant_id}-reference-hr",
            metric="heart_rate",
            unit="bpm",
            start_at=_anchor(record.participant_id),
            times_seconds=times[valid].tolist(),
            values=heart_rate[valid].tolist(),
            metadata={
                "dataset_version": "1.0.0",
                "time_basis": "relative_anchored_not_clinical",
                "reference": "chest_ecg_r_peaks",
                "activity": str(record.metadata["activity"]),
                "motion_channel": "wrist_acceleration_magnitude",
                "dropped_out_of_range_hr_samples": int((~valid).sum()),
            },
        )
    ]


__all__ = ["load_record", "participant_ids", "to_health_events"]
