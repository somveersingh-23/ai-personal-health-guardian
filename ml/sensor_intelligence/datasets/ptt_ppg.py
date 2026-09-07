"""Selective, checksum-pinned adapter for the PhysioNet PTT-PPG dataset."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb
from numpy.typing import NDArray

from sensor_intelligence.datasets.downloader import USER_AGENT, download_resource
from sensor_intelligence.datasets.registry import DATASETS, ResourceSpec
from sensor_intelligence.paths import require_within

BASE_URL = "https://physionet.org/files/pulse-transit-time-ppg/1.1.0"
EXPECTED_RECORDS_SHA256 = "0f142277c6ba294cb7af2318fa0671618b37e89df97e1a9cb41440ed595f3cf4"
EXPECTED_CHECKSUM_MANIFEST_SHA256 = (
    "02b3393e8aecc711a6ec56c19c1c3c9bb6ac0048691780f2c815318dd5c3a3de"
)
EXPECTED_SUBJECT_INFO_SHA256 = (
    "b2353a0acf40b70ea234017de6b19ccce9061d092604c84a94026da58a7f42c5"
)
EXPECTED_RECORD_COUNT = 66
EXPECTED_SUBJECT_COUNT = 22
MAX_PARALLEL_DOWNLOADS = 8
_RECORD_NAME = re.compile(r"^s(?P<subject>[1-9]|1[0-9]|2[0-2])_(?P<activity>sit|walk|run)$")


@dataclass(frozen=True, slots=True)
class PttPpgRecord:
    record_name: str
    participant_id: str
    activity: str
    sampling_rate_hz: float
    distal_channel_1: NDArray[np.float64]
    distal_channel_2: NDArray[np.float64]
    proximal_channel_1: NDArray[np.float64]
    proximal_channel_2: NDArray[np.float64]
    spo2_start_percent: float
    spo2_end_percent: float


def _fetch_bytes(relative_path: str) -> bytes:
    request = urllib.request.Request(
        f"{BASE_URL}/{relative_path}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read()


def _validate_records(raw_records: bytes) -> list[str]:
    if hashlib.sha256(raw_records).hexdigest() != EXPECTED_RECORDS_SHA256:
        raise ValueError("PTT-PPG RECORDS manifest changed")
    records = [line.strip() for line in raw_records.decode("utf-8").splitlines() if line.strip()]
    if len(records) != EXPECTED_RECORD_COUNT or len(set(records)) != len(records):
        raise ValueError("PTT-PPG record count changed")
    parsed = [_RECORD_NAME.fullmatch(record) for record in records]
    if any(match is None for match in parsed):
        raise ValueError("PTT-PPG record naming changed")
    subjects = {match.group("subject") for match in parsed if match is not None}
    if len(subjects) != EXPECTED_SUBJECT_COUNT:
        raise ValueError("PTT-PPG participant count changed")
    return records


def _validate_publisher_checksums(raw_checksums: bytes) -> dict[str, str]:
    if hashlib.sha256(raw_checksums).hexdigest() != EXPECTED_CHECKSUM_MANIFEST_SHA256:
        raise ValueError("PTT-PPG SHA256SUMS manifest changed")
    checksums: dict[str, str] = {}
    for line in raw_checksums.decode("utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative_path = line.split(maxsplit=1)
        relative_path = relative_path.lstrip("* ")
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("PTT-PPG publisher checksum is malformed")
        checksums[relative_path] = expected
    return checksums


def pinned_resources() -> tuple[ResourceSpec, ...]:
    raw_records = _fetch_bytes("RECORDS")
    raw_checksums = _fetch_bytes("SHA256SUMS.txt")
    records = _validate_records(raw_records)
    checksums = _validate_publisher_checksums(raw_checksums)
    required = ["RECORDS", "SHA256SUMS.txt", "csv/subjects_info.csv"]
    required.extend(f"{record}.{suffix}" for record in records for suffix in ("hea", "dat"))
    missing = [path for path in required if path != "SHA256SUMS.txt" and path not in checksums]
    if missing:
        raise ValueError(f"PTT-PPG checksums are missing required files: {missing[0]}")
    resources: list[ResourceSpec] = []
    for relative_path in required:
        if relative_path == "SHA256SUMS.txt":
            expected = EXPECTED_CHECKSUM_MANIFEST_SHA256
            limit = 64 * 1024
        else:
            expected = checksums[relative_path]
            limit = 16 * 1024 * 1024 if relative_path.endswith(".dat") else 128 * 1024
        resources.append(
            ResourceSpec(
                name=relative_path,
                url=f"{BASE_URL}/{relative_path}",
                relative_path=f"raw/ptt-ppg/1.1.0/{relative_path}",
                expected_sha256=expected,
                max_download_bytes=limit,
            )
        )
    return tuple(resources)


def acquire_ptt_ppg(
    root: Path, progress: Callable[[str, int], None] | None = None
) -> dict[str, object]:
    resources = pinned_resources()

    def acquire_one(resource: ResourceSpec) -> dict[str, object]:
        result = download_resource(
            resource,
            root,
            (lambda count, name=resource.name: progress(name, count)) if progress else None,
        )
        return {"name": resource.name, "url": resource.url, **result}

    with ThreadPoolExecutor(
        max_workers=MAX_PARALLEL_DOWNLOADS, thread_name_prefix="ptt-ppg-download"
    ) as executor:
        records = list(executor.map(acquire_one, resources))
    spec = DATASETS["ptt-ppg"]
    provenance = {
        "dataset": spec.key,
        "title": spec.title,
        "version": spec.version,
        "homepage": spec.homepage,
        "license": {"name": spec.license_name, "url": spec.license_url},
        "citation": spec.citation,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "resources": records,
    }
    manifest = require_within(root, root / "manifests" / "ptt-ppg-1.1.0.json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = require_within(root, manifest.with_suffix(".json.tmp"))
    temporary.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    temporary.replace(manifest)
    return provenance


def record_names(root: Path) -> list[str]:
    records_path = root / "RECORDS"
    return _validate_records(records_path.read_bytes())


def load_record(root: Path, record_name: str) -> PttPpgRecord:
    match = _RECORD_NAME.fullmatch(record_name)
    if match is None:
        raise ValueError("PTT-PPG record name is invalid")
    record = wfdb.rdrecord(str(root / record_name))
    if float(record.fs) != 500.0 or record.p_signal is None:
        raise ValueError("PTT-PPG signal format or sampling rate changed")
    names = list(record.sig_name)

    def channel(name: str) -> NDArray[np.float64]:
        if name not in names:
            raise ValueError(f"PTT-PPG channel is missing: {name}")
        values = np.asarray(record.p_signal[:, names.index(name)], dtype=np.float64)
        if values.size == 0 or not np.isfinite(values).all():
            raise ValueError(f"PTT-PPG channel is invalid: {name}")
        return values

    subject_info = pd.read_csv(root / "csv" / "subjects_info.csv")
    row = subject_info.loc[subject_info["record"] == record_name]
    if len(row) != 1:
        raise ValueError("PTT-PPG subject metadata is missing or duplicated")
    return PttPpgRecord(
        record_name=record_name,
        participant_id=f"s{match.group('subject')}",
        activity=match.group("activity"),
        sampling_rate_hz=float(record.fs),
        distal_channel_1=channel("pleth_1"),
        distal_channel_2=channel("pleth_2"),
        proximal_channel_1=channel("pleth_4"),
        proximal_channel_2=channel("pleth_5"),
        spo2_start_percent=float(row.iloc[0]["spo2_start"]),
        spo2_end_percent=float(row.iloc[0]["spo2_end"]),
    )


__all__ = [
    "PttPpgRecord",
    "acquire_ptt_ppg",
    "load_record",
    "pinned_resources",
    "record_names",
]
