"""Adapter for synchronized SensSmartTech PPG, ECG, and accelerometer records.

The source stores each modality as a separate WFDB record with a shared stem.
It is research-only evidence: the PPG is not assumed to be equivalent to an
Android wearable sensor, and ECG-derived HR is used only as an offline reference.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import wfdb
from scipy.signal import butter, find_peaks, sosfiltfilt

from sensor_intelligence.contracts import series_reading
from sensor_intelligence.datasets.records import EventAnnotation, ResearchRecord, SignalChannel

RESEARCH_ANCHOR = datetime(2020, 1, 1, tzinfo=UTC)


def record_ids(dataset_root: Path) -> list[str]:
    suffix = "_ppg.hea"
    identifiers = sorted(
        {path.name.removesuffix(suffix) for path in dataset_root.rglob(f"*{suffix}")}
    )
    if not identifiers:
        raise FileNotFoundError(f"no SensSmartTech PPG headers found below {dataset_root}")
    return identifiers


def participant_ids(dataset_root: Path) -> list[str]:
    participants = sorted(
        {record_id.split("_", maxsplit=1)[0] for record_id in record_ids(dataset_root)}
    )
    if not participants:
        raise FileNotFoundError(f"no SensSmartTech participants found below {dataset_root}")
    return participants


def _record_path(dataset_root: Path, record_id: str, modality: str) -> Path:
    candidates = sorted(dataset_root.rglob(f"{record_id}_{modality}.hea"))
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"expected one SensSmartTech {modality} header for {record_id}, found {len(candidates)}"
        )
    return candidates[0].with_suffix("")


def _read(dataset_root: Path, record_id: str, modality: str) -> tuple[np.ndarray, list[str], float]:
    raw = wfdb.rdrecord(str(_record_path(dataset_root, record_id, modality)))
    values = np.asarray(raw.p_signal, dtype=np.float64)
    names = list(raw.sig_name)
    rate = float(raw.fs)
    if (
        values.ndim != 2
        or values.shape[0] == 0
        or values.shape[1] != len(names)
        or rate <= 0
        or not np.isfinite(values).all()
    ):
        raise ValueError(f"invalid SensSmartTech {modality} record: {record_id}")
    return values, names, rate


def _column(values: np.ndarray, names: list[str], required: str) -> np.ndarray:
    matches = [index for index, name in enumerate(names) if name.lower() == required.lower()]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {required} channel, found {len(matches)}")
    return values[:, matches[0]]


def _ecg_r_peaks(ecg: np.ndarray, rate_hz: float) -> np.ndarray:
    """Return conservative offline R-peak candidates from lead-II ECG.

    This is intentionally only an offline reference extractor. Records without
    plausible peaks are rejected instead of producing an invented HR label.
    """

    if ecg.size < int(rate_hz * 4):
        raise ValueError("SensSmartTech ECG record is too short for reference-HR extraction")
    sos = butter(3, (5.0, 25.0), btype="bandpass", fs=rate_hz, output="sos")
    filtered = sosfiltfilt(sos, ecg)
    integration = np.convolve(
        filtered * filtered,
        np.ones(max(1, int(round(0.12 * rate_hz)))) / max(1, int(round(0.12 * rate_hz))),
        mode="same",
    )
    prominence = max(float(np.std(integration)) * 0.35, np.finfo(float).eps)
    peaks, _ = find_peaks(
        integration,
        distance=max(1, int(round(0.30 * rate_hz))),
        prominence=prominence,
    )
    intervals = np.diff(peaks) / rate_hz
    if peaks.size < 4 or not np.any((intervals >= 0.25) & (intervals <= 2.5)):
        raise ValueError("SensSmartTech ECG has no plausible R-peak sequence")
    return peaks.astype(np.int64)


def load_record(dataset_root: Path, record_id: str) -> ResearchRecord:
    ppg_values, ppg_names, ppg_rate = _read(dataset_root, record_id, "ppg")
    ecg_values, ecg_names, ecg_rate = _read(dataset_root, record_id, "ecg")
    acceleration_values, acceleration_names, acceleration_rate = _read(
        dataset_root, record_id, "acc"
    )
    if ppg_rate != ecg_rate or ppg_rate != acceleration_rate:
        raise ValueError(f"SensSmartTech sample rates do not align for {record_id}")
    if not (
        ppg_values.shape[0] == ecg_values.shape[0] == acceleration_values.shape[0]
    ):
        raise ValueError(f"SensSmartTech sample counts do not align for {record_id}")
    ppg = _column(ppg_values, ppg_names, "carotid_880nm")
    ecg_lead_ii = _column(ecg_values, ecg_names, "II")
    acceleration = _column(acceleration_values, acceleration_names, "az")
    peaks = _ecg_r_peaks(ecg_lead_ii, ppg_rate)
    participant = record_id.split("_", maxsplit=1)[0]
    return ResearchRecord(
        dataset="senssmarttech",
        participant_id=participant,
        duration_seconds=ppg.size / ppg_rate,
        channels={
            "ppg": SignalChannel("ppg", ppg, ppg_rate, "arbitrary_ppg_units"),
            "acceleration": SignalChannel("acceleration", acceleration, ppg_rate, "g"),
        },
        annotations={"ecg_r_peaks": EventAnnotation("ecg_r_peaks", peaks, ppg_rate)},
        metadata={
            "record_id": record_id,
            "ppg_channel": "carotid_880nm",
            "ecg_reference_channel": "II",
            "acceleration_channel": "az",
        },
    )


def _anchor(record_id: str) -> datetime:
    digest = hashlib.sha256(record_id.encode("utf-8")).digest()
    return RESEARCH_ANCHOR + timedelta(days=int.from_bytes(digest[:2], "big") % 365)


def to_health_events(record: ResearchRecord) -> list[dict[str, object]]:
    peaks = record.annotations["ecg_r_peaks"].sample_indices
    intervals = np.diff(peaks) / record.annotations["ecg_r_peaks"].sampling_rate_hz
    heart_rate = 60.0 / intervals
    times = peaks[1:] / record.annotations["ecg_r_peaks"].sampling_rate_hz
    valid = np.isfinite(heart_rate) & (heart_rate >= 25.0) & (heart_rate <= 240.0)
    if not valid.any():
        raise ValueError("SensSmartTech record has no bounded ECG-derived HR")
    record_id = str(record.metadata["record_id"])
    return [
        series_reading(
            dataset="senssmarttech",
            participant=record.participant_id,
            record_type="LeadIIECGDerivedHeartRate",
            record_id=f"senssmarttech-{record_id}-reference-hr",
            metric="heart_rate",
            unit="bpm",
            start_at=_anchor(record_id),
            times_seconds=times[valid].tolist(),
            values=heart_rate[valid].tolist(),
            metadata={
                "dataset_version": "1.0.0",
                "time_basis": "relative_anchored_not_clinical",
                "reference": "lead_ii_ecg_r_peak_algorithm",
                "ppg_channel": str(record.metadata["ppg_channel"]),
                "acceleration_channel": str(record.metadata["acceleration_channel"]),
                "dropped_out_of_range_hr_samples": int((~valid).sum()),
            },
        )
    ]


__all__ = ["load_record", "participant_ids", "record_ids", "to_health_events"]
