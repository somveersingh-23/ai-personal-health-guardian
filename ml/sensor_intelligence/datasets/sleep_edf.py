"""Sleep-EDF expert annotation adapter for session-contract validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyedflib

from sensor_intelligence.contracts import sleep_session_reading

STAGE_MAP = {
    "Sleep stage W": "awake",
    "Sleep stage R": "rem",
    "Sleep stage 1": "light",
    "Sleep stage 2": "light",
    "Sleep stage 3": "deep",
    "Sleep stage 4": "deep",
    "Sleep stage M": "unknown",
    "Sleep stage ?": "unknown",
}


def _utc_start(reader: pyedflib.EdfReader) -> datetime:
    start = reader.getStartdatetime()
    return start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)


def _merge_adjacent(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for stage in stages:
        if (
            merged
            and merged[-1]["stage"] == stage["stage"]
            and merged[-1]["end_at"] == stage["start_at"]
        ):
            merged[-1]["end_at"] = stage["end_at"]
        else:
            merged.append(stage.copy())
    return merged


def load_expert_session(
    hypnogram_path: Path, psg_path: Path | None = None
) -> dict[str, Any]:
    if not hypnogram_path.name.endswith("-Hypnogram.edf"):
        raise ValueError("expected a Sleep-EDF hypnogram file")
    reader = pyedflib.EdfReader(str(hypnogram_path))
    try:
        recording_start = _utc_start(reader)
        onsets, durations, descriptions = reader.readAnnotations()
    finally:
        reader.close()

    stages: list[dict[str, Any]] = []
    for onset, duration, description in zip(onsets, durations, descriptions, strict=True):
        label = STAGE_MAP.get(str(description))
        if label is None or float(duration) <= 0:
            continue
        start = recording_start + timedelta(seconds=float(onset))
        end = start + timedelta(seconds=float(duration))
        stages.append({"start_at": start, "end_at": end, "stage": label})

    scored_sleep = [
        index for index, stage in enumerate(stages) if stage["stage"] in {"light", "deep", "rem"}
    ]
    if not scored_sleep:
        raise ValueError("hypnogram contains no scored sleep")
    trimmed = stages[scored_sleep[0] : scored_sleep[-1] + 1]
    merged = _merge_adjacent(trimmed)
    if len(merged) > 500:
        raise ValueError("merged Sleep-EDF stages exceed backend contract limit")
    session_start = merged[0]["start_at"]
    session_end = merged[-1]["end_at"]
    psg_metadata: dict[str, Any] = {"psg_pair_validated": False}
    if psg_path is not None:
        if not psg_path.name.endswith("-PSG.edf"):
            raise ValueError("expected a Sleep-EDF PSG file")
        psg_reader = pyedflib.EdfReader(str(psg_path))
        try:
            psg_start = _utc_start(psg_reader)
            psg_end = psg_start + timedelta(seconds=float(psg_reader.file_duration))
        finally:
            psg_reader.close()
        if session_start < psg_start or session_end > psg_end:
            raise ValueError("Sleep-EDF hypnogram stages fall outside the paired PSG")
        psg_metadata = {
            "psg_pair_validated": True,
            "psg_file": psg_path.name,
            "psg_duration_seconds": float((psg_end - psg_start).total_seconds()),
        }
    participant = hypnogram_path.name[:6]
    serialized_stages = [
        {
            "start_at": stage["start_at"].isoformat(),
            "end_at": stage["end_at"].isoformat(),
            "stage": stage["stage"],
        }
        for stage in merged
    ]
    return sleep_session_reading(
        dataset="sleep-edf",
        participant=participant,
        record_id=hypnogram_path.stem,
        start_at=session_start,
        end_at=session_end,
        stages=serialized_stages,
        metadata={
            "dataset_version": "1.0.0",
            "scoring_standard": "Rechtschaffen_and_Kales_1968",
            "timezone_basis": "dataset_naive_assumed_utc",
            "source_annotations": len(stages),
            "merged_stages": len(merged),
            **psg_metadata,
        },
    )
