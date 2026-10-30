"""BIDMC CSV adapter with reference numerics and breath annotations."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sensor_intelligence.contracts import instant_reading, series_reading
from sensor_intelligence.datasets.models import EventAnnotation, ResearchRecord, SignalChannel

BIDMC_SIGNAL_RATE_HZ = 125.0
BIDMC_NUMERIC_RATE_HZ = 1.0
RESEARCH_ANCHOR = datetime(2000, 1, 1, tzinfo=UTC)


def _normalized_columns(frame: pd.DataFrame) -> dict[str, str]:
    return {
        re.sub(r"[^a-z0-9]+", "", str(column).lower()): str(column)
        for column in frame.columns
    }


def _column(frame: pd.DataFrame, *aliases: str) -> np.ndarray:
    normalized = _normalized_columns(frame)
    for alias in aliases:
        key = re.sub(r"[^a-z0-9]+", "", alias.lower())
        if key in normalized:
            values = pd.to_numeric(frame[normalized[key]], errors="coerce").to_numpy(dtype=float)
            return values
    raise KeyError(f"none of the columns {aliases!r} exist; available={list(frame.columns)!r}")


def _optional_column(frame: pd.DataFrame, *aliases: str) -> np.ndarray | None:
    try:
        return _column(frame, *aliases)
    except KeyError:
        return None


def _annotation_indices(frame: pd.DataFrame, column: str) -> tuple[np.ndarray, int]:
    numeric = pd.to_numeric(frame[column], errors="coerce").dropna().to_numpy(dtype=float)
    if numeric.size == 0 or not np.equal(numeric, np.floor(numeric)).all():
        raise ValueError(f"BIDMC annotation column {column!r} has invalid sample indices")
    indices = numeric.astype(np.int64)
    normalized = np.unique(indices)
    correction_count = int(np.sum(np.diff(indices) < 0) + (indices.size - normalized.size))
    return normalized, correction_count


def locate_csv_root(dataset_root: Path) -> Path:
    candidates = sorted(dataset_root.rglob("bidmc_01_Signals.csv"))
    if not candidates:
        raise FileNotFoundError(f"BIDMC CSV files not found below {dataset_root}")
    return candidates[0].parent


def participant_ids(dataset_root: Path) -> list[str]:
    csv_root = locate_csv_root(dataset_root)
    return sorted(path.name.split("_")[1] for path in csv_root.glob("bidmc_*_Signals.csv"))


def load_record(dataset_root: Path, participant_id: str) -> ResearchRecord:
    if not re.fullmatch(r"\d{2}", participant_id):
        raise ValueError("BIDMC participant identifier must contain two digits")
    csv_root = locate_csv_root(dataset_root)
    signals = pd.read_csv(csv_root / f"bidmc_{participant_id}_Signals.csv")
    numerics = pd.read_csv(csv_root / f"bidmc_{participant_id}_Numerics.csv")
    breaths = pd.read_csv(csv_root / f"bidmc_{participant_id}_Breaths.csv")

    ppg = _column(signals, "PLETH", "PPG")
    respiration = _column(signals, "RESP", "RESPIRATION")
    ecg = _column(signals, "II", "ECG")
    channels = {
        "ppg": SignalChannel("ppg", ppg, BIDMC_SIGNAL_RATE_HZ, "a.u."),
        "respiration": SignalChannel(
            "respiration", respiration, BIDMC_SIGNAL_RATE_HZ, "a.u."
        ),
        "ecg": SignalChannel("ecg", ecg, BIDMC_SIGNAL_RATE_HZ, "mV"),
    }

    references: dict[str, SignalChannel] = {}
    numeric_aliases = {
        "heart_rate": ("HR", "HEART RATE"),
        "pulse_rate": ("PULSE", "PULSE RATE"),
        "respiration_rate": ("RESP", "RESPIRATORY RATE"),
        "spo2": ("SpO2", "OXYGEN SATURATION"),
    }
    for name, aliases in numeric_aliases.items():
        values = _optional_column(numerics, *aliases)
        if values is not None:
            finite = np.isfinite(values)
            cleaned = np.where(finite, values, np.nan)
            references[name] = SignalChannel(
                name,
                np.nan_to_num(cleaned, nan=-1.0),
                BIDMC_NUMERIC_RATE_HZ,
                "%" if name == "spo2" else ("breaths/min" if name == "respiration_rate" else "bpm"),
            )

    duration = min(channel.values.size / channel.sampling_rate_hz for channel in channels.values())
    annotation_columns = list(breaths.columns)
    if len(annotation_columns) != 2:
        raise ValueError("BIDMC breaths file must contain exactly two annotators")
    parsed_annotations = [
        _annotation_indices(breaths, column) for column in annotation_columns
    ]
    annotations = {
        f"breaths_annotator_{index + 1}": EventAnnotation(
            name=f"breaths_annotator_{index + 1}",
            sample_indices=parsed_annotations[index][0],
            sampling_rate_hz=BIDMC_SIGNAL_RATE_HZ,
        )
        for index, column in enumerate(annotation_columns)
    }
    return ResearchRecord(
        dataset="bidmc",
        participant_id=participant_id,
        duration_seconds=float(duration),
        channels=channels,
        references=references,
        annotations=annotations,
        metadata={
            "clinical_context": "critical_care",
            "waveform_sampling_rate_hz": BIDMC_SIGNAL_RATE_HZ,
            "numeric_sampling_rate_hz": BIDMC_NUMERIC_RATE_HZ,
            "breath_annotation_order_corrections": sum(
                correction_count for _, correction_count in parsed_annotations
            ),
        },
    )


def to_health_events(record: ResearchRecord) -> list[dict[str, Any]]:
    """Convert reference numerics; -1 sentinels are treated as missing, never as measurements."""

    anchor = RESEARCH_ANCHOR + timedelta(days=int(record.participant_id))
    common_metadata = {
        "dataset_version": "1.0.0",
        "time_basis": "relative_anchored_not_clinical",
        "clinical_context": "critical_care",
    }
    events: list[dict[str, Any]] = []
    heart_rate = record.references.get("heart_rate")
    if heart_rate is not None:
        valid = np.flatnonzero(heart_rate.values >= 0)
        if valid.size >= 2:
            events.append(
                series_reading(
                    dataset="bidmc",
                    participant=record.participant_id,
                    record_type="BIDMCReferenceHeartRate",
                    record_id=f"bidmc-{record.participant_id}-hr",
                    metric="heart_rate",
                    unit="bpm",
                    start_at=anchor,
                    times_seconds=(valid / heart_rate.sampling_rate_hz).astype(float).tolist(),
                    values=heart_rate.values[valid].astype(float).tolist(),
                    metadata=common_metadata,
                )
            )
    for reference_name, metric, unit in (
        ("respiration_rate", "respiration_rate", "breaths/min"),
        ("spo2", "spo2", "%"),
    ):
        channel = record.references.get(reference_name)
        if channel is None:
            continue
        for index in np.flatnonzero(channel.values >= 0):
            observed = anchor + timedelta(seconds=float(index / channel.sampling_rate_hz))
            events.append(
                instant_reading(
                    dataset="bidmc",
                    participant=record.participant_id,
                    record_type=f"BIDMCReference{reference_name.title().replace('_', '')}",
                    record_id=f"bidmc-{record.participant_id}-{reference_name}-{index}",
                    metric=metric,
                    unit=unit,
                    observed_at=observed,
                    value=float(channel.values[index]),
                    metadata=common_metadata,
                )
            )
    return events
