"""Dataset-aligned PPG windows with participant provenance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sensor_intelligence.datasets.models import ResearchRecord


@dataclass(frozen=True, slots=True)
class WindowObservation:
    dataset: str
    participant_id: str
    window_index: int
    ppg: NDArray[np.float64]
    ppg_rate_hz: float
    acceleration: NDArray[np.float64] | None
    acceleration_rate_hz: float | None
    reference_heart_rate_bpm: float
    activity_id: int | None = None


def ppg_dalia_windows(
    record: ResearchRecord, window_seconds: float = 8.0, stride_seconds: float = 2.0
) -> list[WindowObservation]:
    """Follow the dataset authors' 8-second window / 2-second stride label alignment."""

    ppg = record.channel("ppg")
    acceleration = record.channel("acceleration")
    activity = record.channels.get("activity")
    labels = record.references["heart_rate"].values
    ppg_width = int(round(window_seconds * ppg.sampling_rate_hz))
    ppg_stride = int(round(stride_seconds * ppg.sampling_rate_hz))
    acc_width = int(round(window_seconds * acceleration.sampling_rate_hz))
    acc_stride = int(round(stride_seconds * acceleration.sampling_rate_hz))
    windows: list[WindowObservation] = []
    for index, reference in enumerate(labels):
        ppg_start = index * ppg_stride
        acc_start = index * acc_stride
        if (
            ppg_start + ppg_width > ppg.values.size
            or acc_start + acc_width > acceleration.values.size
        ):
            break
        if not 25.0 <= float(reference) <= 240.0:
            continue
        activity_id: int | None = None
        if activity is not None:
            activity_start = int(round(index * stride_seconds * activity.sampling_rate_hz))
            activity_end = activity_start + int(
                round(window_seconds * activity.sampling_rate_hz)
            )
            activity_labels = activity.values[activity_start:activity_end].astype(int)
            if activity_labels.size:
                values, counts = np.unique(activity_labels, return_counts=True)
                activity_id = int(values[int(np.argmax(counts))])
        windows.append(
            WindowObservation(
                dataset=record.dataset,
                participant_id=record.participant_id,
                window_index=index,
                ppg=ppg.values[ppg_start : ppg_start + ppg_width],
                ppg_rate_hz=ppg.sampling_rate_hz,
                acceleration=acceleration.values[acc_start : acc_start + acc_width],
                acceleration_rate_hz=acceleration.sampling_rate_hz,
                reference_heart_rate_bpm=float(reference),
                activity_id=activity_id,
            )
        )
    return windows


def bidmc_windows(
    record: ResearchRecord, window_seconds: float = 8.0, stride_seconds: float = 2.0
) -> list[WindowObservation]:
    ppg = record.channel("ppg")
    reference = record.references["heart_rate"]
    ppg_width = int(round(window_seconds * ppg.sampling_rate_hz))
    ppg_stride = int(round(stride_seconds * ppg.sampling_rate_hz))
    windows: list[WindowObservation] = []
    for window_index, ppg_start in enumerate(range(0, ppg.values.size - ppg_width + 1, ppg_stride)):
        start_seconds = ppg_start / ppg.sampling_rate_hz
        ref_start = int(np.floor(start_seconds * reference.sampling_rate_hz))
        ref_end = int(np.ceil((start_seconds + window_seconds) * reference.sampling_rate_hz))
        values = reference.values[ref_start:ref_end]
        values = values[(values >= 25.0) & (values <= 240.0)]
        if not values.size:
            continue
        windows.append(
            WindowObservation(
                dataset=record.dataset,
                participant_id=record.participant_id,
                window_index=window_index,
                ppg=ppg.values[ppg_start : ppg_start + ppg_width],
                ppg_rate_hz=ppg.sampling_rate_hz,
                acceleration=None,
                acceleration_rate_hz=None,
                reference_heart_rate_bpm=float(np.median(values)),
            )
        )
    return windows


def senssmarttech_windows(
    record: ResearchRecord, window_seconds: float = 8.0, stride_seconds: float = 2.0
) -> list[WindowObservation]:
    """Create windows against a contemporaneous ECG-derived HR reference."""

    ppg = record.channel("ppg")
    acceleration = record.channel("acceleration")
    peaks = record.annotations["ecg_r_peaks"]
    width = int(round(window_seconds * ppg.sampling_rate_hz))
    stride = int(round(stride_seconds * ppg.sampling_rate_hz))
    windows: list[WindowObservation] = []
    for window_index, start in enumerate(range(0, ppg.values.size - width + 1, stride)):
        end = start + width
        in_window = peaks.sample_indices[
            (peaks.sample_indices >= start) & (peaks.sample_indices < end)
        ]
        if in_window.size < 3:
            continue
        intervals = np.diff(in_window) / peaks.sampling_rate_hz
        intervals = intervals[(intervals >= 0.25) & (intervals <= 2.4)]
        if intervals.size < 2:
            continue
        reference = float(60.0 / np.median(intervals))
        windows.append(
            WindowObservation(
                dataset=record.dataset,
                participant_id=record.participant_id,
                window_index=window_index,
                ppg=ppg.values[start:end],
                ppg_rate_hz=ppg.sampling_rate_hz,
                acceleration=acceleration.values[start:end],
                acceleration_rate_hz=acceleration.sampling_rate_hz,
                reference_heart_rate_bpm=reference,
            )
        )
    return windows


def wrist_exercise_windows(
    record: ResearchRecord, window_seconds: float = 8.0, stride_seconds: float = 2.0
) -> list[WindowObservation]:
    """Create wrist PPG windows against the dataset's chest-ECG R-peak reference."""

    ppg = record.channel("ppg")
    acceleration = record.channel("acceleration_magnitude")
    peaks = record.annotations["ecg_r_peaks"]
    width = int(round(window_seconds * ppg.sampling_rate_hz))
    stride = int(round(stride_seconds * ppg.sampling_rate_hz))
    windows: list[WindowObservation] = []
    for window_index, start in enumerate(range(0, ppg.values.size - width + 1, stride)):
        end = start + width
        in_window = peaks.sample_indices[
            (peaks.sample_indices >= start) & (peaks.sample_indices < end)
        ]
        if in_window.size < 3:
            continue
        intervals = np.diff(in_window) / peaks.sampling_rate_hz
        intervals = intervals[(intervals >= 0.25) & (intervals <= 2.4)]
        if intervals.size < 2:
            continue
        windows.append(
            WindowObservation(
                dataset=record.dataset,
                participant_id=record.participant_id,
                window_index=window_index,
                ppg=ppg.values[start:end],
                ppg_rate_hz=ppg.sampling_rate_hz,
                acceleration=acceleration.values[start:end],
                acceleration_rate_hz=acceleration.sampling_rate_hz,
                reference_heart_rate_bpm=float(60.0 / np.median(intervals)),
            )
        )
    return windows
