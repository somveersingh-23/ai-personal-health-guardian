"""PPG-DaLiA adapter with a restricted NumPy pickle loader."""

from __future__ import annotations

import builtins
import importlib
import json
import os
import pickle
import re
import zipfile
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np

from sensor_intelligence.contracts import series_reading
from sensor_intelligence.datasets.downloader import sha256_file
from sensor_intelligence.datasets.models import ResearchRecord, SignalChannel
from sensor_intelligence.datasets.registry import DATASETS
from sensor_intelligence.paths import require_within

PPG_RATE_HZ = 64.0
WRIST_ACCEL_RATE_HZ = 32.0
WRIST_TEMPERATURE_RATE_HZ = 4.0
REFERENCE_HR_RATE_HZ = 0.5
ACTIVITY_RATE_HZ = 4.0
RESEARCH_ANCHOR = datetime(2001, 1, 1, tzinfo=UTC)
CACHE_SCHEMA_VERSION = "1.0.0"

_ALLOWED_GLOBALS = {
    ("builtins", "dict"),
    ("builtins", "list"),
    ("builtins", "set"),
    ("builtins", "slice"),
    ("builtins", "tuple"),
    ("numpy", "dtype"),
    ("numpy", "ndarray"),
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy.core.multiarray", "scalar"),
}


class RestrictedNumpyUnpickler(pickle.Unpickler):
    """Allow only the globals required to reconstruct plain NumPy containers."""

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) not in _ALLOWED_GLOBALS:
            raise pickle.UnpicklingError(f"forbidden pickle global: {module}.{name}")
        if module == "builtins":
            return getattr(builtins, name)
        imported = importlib.import_module(module)
        return getattr(imported, name)


def restricted_load_stream(handle: BinaryIO) -> dict[str, Any]:
    payload = RestrictedNumpyUnpickler(handle, encoding="latin1").load()
    if not isinstance(payload, dict):
        raise ValueError("PPG-DaLiA participant payload must be a dictionary")
    return payload


def restricted_load(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return restricted_load_stream(handle)


def locate_participant(dataset_root: Path, participant_id: str) -> Path:
    if not re.fullmatch(r"S(?:[1-9]|1[0-5])", participant_id):
        raise ValueError("PPG-DaLiA participant must be S1 through S15")
    candidates = sorted(dataset_root.rglob(f"{participant_id}.pkl"))
    if not candidates:
        raise FileNotFoundError(f"{participant_id}.pkl not found below {dataset_root}")
    return candidates[0]


def participant_ids(dataset_root: Path) -> list[str]:
    identifiers = {
        path.stem for path in dataset_root.rglob("S*.pkl") if re.fullmatch(r"S\d+", path.stem)
    }
    if not identifiers:
        archives = sorted(dataset_root.rglob("data.zip"))
        if len(archives) != 1:
            raise FileNotFoundError(
                f"expected one PPG-DaLiA data.zip below {dataset_root}"
            ) from None
        with zipfile.ZipFile(archives[0]) as bundle:
            identifiers = {
                match.group(1)
                for name in bundle.namelist()
                if (match := re.fullmatch(r"(?:.*/)?(S(?:[1-9]|1[0-5]))/\1\.pkl", name))
            }
    return sorted(identifiers, key=lambda value: int(value[1:]))


def _load_payload(dataset_root: Path, participant_id: str) -> dict[str, Any]:
    try:
        return restricted_load(locate_participant(dataset_root, participant_id))
    except FileNotFoundError:
        archives = sorted(dataset_root.rglob("data.zip"))
        if len(archives) != 1:
            raise FileNotFoundError(
                f"expected one PPG-DaLiA data.zip below {dataset_root}"
            ) from None
        with zipfile.ZipFile(archives[0]) as bundle:
            matches = [
                name
                for name in bundle.namelist()
                if re.fullmatch(rf"(?:.*/)?{participant_id}/{participant_id}\.pkl", name)
            ]
            if len(matches) != 1:
                raise FileNotFoundError(
                    f"expected one {participant_id}.pkl inside PPG-DaLiA data.zip"
                ) from None
            with bundle.open(matches[0]) as handle:
                return restricted_load_stream(handle)


def _one_dimensional(value: Any, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float).squeeze()
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"PPG-DaLiA {name} must be one-dimensional")
    if not np.isfinite(array).all():
        raise ValueError(f"PPG-DaLiA {name} contains non-finite values")
    return array.astype(np.float64, copy=False)


def _record_from_payload(payload: dict[str, Any], participant_id: str) -> ResearchRecord:
    try:
        wrist = payload["signal"]["wrist"]
        bvp = _one_dimensional(wrist["BVP"], "wrist BVP")
        acceleration = np.asarray(wrist["ACC"], dtype=float)
        temperature = _one_dimensional(wrist["TEMP"], "wrist temperature")
        reference_hr = _one_dimensional(payload["label"], "reference heart rate")
    except (KeyError, TypeError) as exc:
        raise ValueError("unexpected PPG-DaLiA participant structure") from exc
    if acceleration.ndim != 2 or acceleration.shape[1] != 3:
        raise ValueError("PPG-DaLiA wrist acceleration must have three axes")
    if not np.isfinite(acceleration).all():
        raise ValueError("PPG-DaLiA wrist acceleration contains non-finite values")
    acceleration_magnitude = np.linalg.norm(acceleration, axis=1).astype(np.float64)

    duration = bvp.size / PPG_RATE_HZ
    channels = {
        "ppg": SignalChannel("ppg", bvp, PPG_RATE_HZ, "a.u."),
        "acceleration": SignalChannel(
            "acceleration", acceleration_magnitude, WRIST_ACCEL_RATE_HZ, "g"
        ),
        "skin_temperature": SignalChannel(
            "skin_temperature",
            temperature,
            WRIST_TEMPERATURE_RATE_HZ,
            "degC",
        ),
    }
    if "activity" in payload:
        channels["activity"] = SignalChannel(
            "activity",
            _one_dimensional(payload["activity"], "activity label"),
            ACTIVITY_RATE_HZ,
            "class_id",
        )
    return ResearchRecord(
        dataset="ppg-dalia",
        participant_id=participant_id,
        duration_seconds=float(duration),
        channels=channels,
        references={
            "heart_rate": SignalChannel(
                "heart_rate", reference_hr, REFERENCE_HR_RATE_HZ, "bpm"
            )
        },
        metadata={
            "setting": "daily_life_activities",
            "reference": "ecg_derived_heart_rate",
            "ppg_sampling_rate_hz": PPG_RATE_HZ,
            "acceleration_sampling_rate_hz": WRIST_ACCEL_RATE_HZ,
        },
    )


def _cache_path(dataset_root: Path, participant_id: str) -> Path:
    if not re.fullmatch(r"S(?:[1-9]|1[0-5])", participant_id):
        raise ValueError("PPG-DaLiA participant must be S1 through S15")
    data_directory = dataset_root.parents[2]
    return require_within(
        data_directory,
        data_directory / "processed" / "ppg-dalia" / "1.0" / f"{participant_id}.npz",
    )


def _record_from_cache(path: Path, participant_id: str) -> ResearchRecord:
    with np.load(path, allow_pickle=False) as cache:
        if str(cache["schema_version"].item()) != CACHE_SCHEMA_VERSION:
            raise ValueError(f"unsupported PPG-DaLiA cache schema: {path}")
        channels = {
            "ppg": SignalChannel("ppg", cache["ppg"], PPG_RATE_HZ, "a.u."),
            "acceleration": SignalChannel(
                "acceleration", cache["acceleration"], WRIST_ACCEL_RATE_HZ, "g"
            ),
            "skin_temperature": SignalChannel(
                "skin_temperature", cache["skin_temperature"], WRIST_TEMPERATURE_RATE_HZ, "degC"
            ),
        }
        if "activity" in cache.files:
            channels["activity"] = SignalChannel(
                "activity", cache["activity"], ACTIVITY_RATE_HZ, "class_id"
            )
        heart_rate = cache["heart_rate"]
    return ResearchRecord(
        dataset="ppg-dalia",
        participant_id=participant_id,
        duration_seconds=float(channels["ppg"].values.size / PPG_RATE_HZ),
        channels=channels,
        references={
            "heart_rate": SignalChannel(
                "heart_rate", heart_rate, REFERENCE_HR_RATE_HZ, "bpm"
            )
        },
        metadata={
            "setting": "daily_life_activities",
            "reference": "ecg_derived_heart_rate",
            "ppg_sampling_rate_hz": PPG_RATE_HZ,
            "acceleration_sampling_rate_hz": WRIST_ACCEL_RATE_HZ,
            "processed_cache_schema": CACHE_SCHEMA_VERSION,
        },
    )


@lru_cache(maxsize=32)
def _verify_cache(path: Path, participant_id: str) -> None:
    manifest_path = path.parent / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"PPG-DaLiA cache manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_source = DATASETS["ppg-dalia"].resources[0].expected_sha256
    if manifest.get("source_archive_sha256") != expected_source:
        raise ValueError("PPG-DaLiA cache source hash does not match the approved registry")
    expected_records = {
        record["participant"]: record["sha256"] for record in manifest.get("records", [])
    }
    if participant_id not in expected_records:
        raise ValueError(f"PPG-DaLiA cache manifest has no {participant_id} record")
    if sha256_file(path) != expected_records[participant_id]:
        raise ValueError(f"PPG-DaLiA cache checksum mismatch: {participant_id}")


def load_record(dataset_root: Path, participant_id: str) -> ResearchRecord:
    cache = _cache_path(dataset_root, participant_id)
    if cache.is_file():
        _verify_cache(cache, participant_id)
        return _record_from_cache(cache, participant_id)
    return _record_from_payload(_load_payload(dataset_root, participant_id), participant_id)


def prepare_cache(dataset_root: Path) -> dict[str, Any]:
    """Create minimized, non-pickle synchronized caches from the pinned official archive."""

    data_directory = dataset_root.parents[2]
    source_manifest = data_directory / "manifests" / "ppg-dalia-1.0.json"
    provenance = json.loads(source_manifest.read_text(encoding="utf-8"))
    source_sha256 = provenance["resources"][0]["sha256"]
    expected_source = DATASETS["ppg-dalia"].resources[0].expected_sha256
    if source_sha256 != expected_source:
        raise ValueError("PPG-DaLiA source manifest does not match the approved registry")
    records: list[dict[str, Any]] = []
    for participant_id in participant_ids(dataset_root):
        record = _record_from_payload(
            _load_payload(dataset_root, participant_id), participant_id
        )
        destination = _cache_path(dataset_root, participant_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = require_within(
            data_directory, destination.with_suffix(destination.suffix + ".part")
        )
        arrays: dict[str, Any] = {
            "schema_version": np.asarray(CACHE_SCHEMA_VERSION),
            "ppg": record.channel("ppg").values,
            "acceleration": record.channel("acceleration").values,
            "skin_temperature": record.channel("skin_temperature").values,
            "heart_rate": record.references["heart_rate"].values,
        }
        if "activity" in record.channels:
            arrays["activity"] = record.channel("activity").values
        with temporary.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
        records.append(
            {
                "participant": participant_id,
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        )
    manifest = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "dataset": "ppg-dalia",
        "source_archive_sha256": source_sha256,
        "contents": "wrist_ppg_acceleration_temperature_activity_and_ecg_derived_hr",
        "records": records,
    }
    manifest_path = require_within(
        data_directory,
        data_directory / "processed" / "ppg-dalia" / "1.0" / "manifest.json",
    )
    temporary_manifest = require_within(
        data_directory, manifest_path.with_suffix(".json.part")
    )
    temporary_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temporary_manifest.replace(manifest_path)
    return manifest


def to_health_events(record: ResearchRecord) -> list[dict[str, Any]]:
    """Convert derived/reference signals, never the high-rate raw research waveform."""

    participant_number = int(record.participant_id[1:])
    anchor = RESEARCH_ANCHOR + timedelta(days=participant_number)
    metadata = {
        "dataset_version": "1.0",
        "time_basis": "relative_anchored_not_clinical",
        "setting": "daily_life_activities",
    }
    events: list[dict[str, Any]] = []
    for channel, metric, unit, record_type in (
        (
            record.references["heart_rate"],
            "heart_rate",
            "bpm",
            "PPGDaLiAECGDerivedHeartRate",
        ),
        (
            record.channels["skin_temperature"],
            "skin_temperature",
            "degC",
            "PPGDaLiAWristTemperature",
        ),
    ):
        for chunk_index, start in enumerate(range(0, channel.values.size, 9_000)):
            chunk = channel.values[start : start + 9_000]
            if chunk.size < 2:
                continue
            chunk_start = anchor + timedelta(seconds=start / channel.sampling_rate_hz)
            times = (np.arange(chunk.size) / channel.sampling_rate_hz).astype(float)
            events.append(
                series_reading(
                    dataset="ppg-dalia",
                    participant=record.participant_id,
                    record_type=record_type,
                    record_id=(
                        f"ppg-dalia-{record.participant_id}-{metric}-{chunk_index:03d}"
                    ),
                    metric=metric,
                    unit=unit,
                    start_at=chunk_start,
                    times_seconds=times.tolist(),
                    values=chunk.astype(float).tolist(),
                    metadata={**metadata, "chunk_index": chunk_index},
                )
            )
    return events
