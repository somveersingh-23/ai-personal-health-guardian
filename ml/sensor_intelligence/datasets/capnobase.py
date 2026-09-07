"""Pinned CapnoBase acquisition and benchmark-only PPG/RR adapter.

CapnoBase explicitly reserves these records for independent benchmarking. The
adapter therefore exposes no training split and the benchmark must remain
untuned after the BIDMC development experiment.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from sensor_intelligence.datasets.downloader import USER_AGENT, download_resource
from sensor_intelligence.datasets.registry import DATASETS, ResourceSpec
from sensor_intelligence.paths import require_within

PERSISTENT_ID = "doi:10.5683/SP2/NLB8IT"
DATAVERSE_API = "https://borealisdata.ca/api"
EXPECTED_VERSION = "1.1"
EXPECTED_FILE_COUNT = 84
EXPECTED_CASE_COUNT = 42
EXPECTED_MANIFEST_SHA256 = (
    "15272b91f86047a76b5ef0f9ce803f048b6df20dd68d016bba3acc467e4240de"
)
SIGNAL_RATE_HZ = 300.0
MAX_TOTAL_DOWNLOAD_BYTES = 128 * 1024 * 1024
_LABEL = re.compile(r"^(?P<case>[0-9]{4})_8min_(?P<kind>signal|reference)\.tab$")


@dataclass(frozen=True, slots=True)
class CapnoBaseRecord:
    case_id: str
    ppg: NDArray[np.float64]
    ppg_rate_hz: float
    reference_times_seconds: NDArray[np.float64]
    reference_respiration_bpm: NDArray[np.float64]
    excluded_reference_points: int


def _canonical_file_manifest(version_payload: dict[str, Any]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for entry in version_payload.get("files", []):
        label = str(entry.get("label", ""))
        if not _LABEL.fullmatch(label):
            continue
        data_file = entry.get("dataFile", {})
        checksum = data_file.get("checksum", {})
        if checksum.get("type") != "MD5":
            raise ValueError(f"CapnoBase publisher checksum is not MD5: {label}")
        md5 = str(checksum.get("value", "")).lower()
        if len(md5) != 32 or any(character not in "0123456789abcdef" for character in md5):
            raise ValueError(f"CapnoBase publisher checksum is invalid: {label}")
        files.append(
            {
                "bytes": int(data_file["filesize"]),
                "directory": str(entry.get("directoryLabel", "")),
                "id": int(data_file["id"]),
                "label": label,
                "md5": md5,
            }
        )
    files.sort(key=lambda item: item["label"])
    return files


def validate_metadata(version_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate version, pair completeness and the pinned publisher file manifest."""

    version = f"{version_payload.get('versionNumber')}.{version_payload.get('versionMinorNumber')}"
    if version != EXPECTED_VERSION or version_payload.get("versionState") != "RELEASED":
        raise ValueError(f"unexpected CapnoBase release: {version}")
    files = _canonical_file_manifest(version_payload)
    if len(files) != EXPECTED_FILE_COUNT:
        raise ValueError("CapnoBase benchmark file count changed")
    if any(item["directory"] != "data/csv" for item in files):
        raise ValueError("CapnoBase benchmark file directory changed")
    if sum(int(item["bytes"]) for item in files) > MAX_TOTAL_DOWNLOAD_BYTES:
        raise ValueError("CapnoBase benchmark exceeds the approved download bound")

    pairs: dict[str, set[str]] = {}
    for item in files:
        match = _LABEL.fullmatch(str(item["label"]))
        if match is None:  # pragma: no cover - already filtered above
            raise AssertionError("validated label did not match")
        pairs.setdefault(match.group("case"), set()).add(match.group("kind"))
    if len(pairs) != EXPECTED_CASE_COUNT or any(
        kinds != {"signal", "reference"} for kinds in pairs.values()
    ):
        raise ValueError("CapnoBase signal/reference pairing changed")

    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != EXPECTED_MANIFEST_SHA256:
        raise ValueError("CapnoBase publisher file manifest changed")
    return files


def fetch_pinned_manifest() -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"persistentId": PERSISTENT_ID})
    request = urllib.request.Request(
        f"{DATAVERSE_API}/datasets/:persistentId/?{query}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        payload = json.load(response)
    if payload.get("status") != "OK":
        raise ValueError("CapnoBase Dataverse metadata request failed")
    return validate_metadata(payload["data"]["latestVersion"])


def acquire_capnobase(
    root: Path,
    *,
    terms_accepted: bool,
    progress: Callable[[str, int], None] | None = None,
) -> dict[str, object]:
    if not terms_accepted:
        raise PermissionError(
            "CapnoBase requires --accept-dataset-terms after reviewing its DOI page"
        )
    files = fetch_pinned_manifest()
    records: list[dict[str, object]] = []
    for item in files:
        label = str(item["label"])
        resource = ResourceSpec(
            name=label,
            url=f"{DATAVERSE_API}/access/datafile/{item['id']}?format=original",
            relative_path=f"raw/capnobase/{EXPECTED_VERSION}/data/csv/{label}",
            expected_md5=str(item["md5"]),
            # Dataverse's tabular metadata size can differ slightly from the
            # original CSV byte stream; publisher MD5 remains authoritative.
            max_download_bytes=int(item["bytes"]) + 1024 * 1024,
        )
        record = download_resource(
            resource,
            root,
            (lambda count, name=label: progress(name, count)) if progress else None,
        )
        records.append({"name": label, "url": resource.url, **record})

    spec = DATASETS["capnobase"]
    provenance = {
        "dataset": spec.key,
        "title": spec.title,
        "version": spec.version,
        "homepage": spec.homepage,
        "license": {"name": spec.license_name, "url": spec.license_url},
        "citation": spec.citation,
        "dataset_terms_explicitly_accepted": True,
        "pinned_file_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "resources": records,
    }
    manifest = require_within(root, root / "manifests" / "capnobase-1.1.json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = require_within(root, manifest.with_suffix(".json.tmp"))
    temporary.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    temporary.replace(manifest)
    return provenance


def _csv_root(root: Path) -> Path:
    candidate = root / "data" / "csv"
    if not candidate.is_dir():
        raise FileNotFoundError(f"CapnoBase CSV directory is missing: {candidate}")
    return candidate


def case_ids(root: Path) -> list[str]:
    csv_root = _csv_root(root)
    signals = {path.name.split("_", 1)[0] for path in csv_root.glob("*_8min_signal.tab")}
    references = {
        path.name.split("_", 1)[0] for path in csv_root.glob("*_8min_reference.tab")
    }
    if signals != references or len(signals) != EXPECTED_CASE_COUNT:
        raise ValueError("CapnoBase local signal/reference set is incomplete")
    return sorted(signals)


def _space_separated_vector(frame: pd.DataFrame, column: str) -> NDArray[np.float64]:
    if frame.empty or column not in frame:
        raise ValueError(f"CapnoBase reference column is missing: {column}")
    values = np.fromstring(str(frame.iloc[0][column]), sep=" ", dtype=np.float64)
    if values.size < 2:
        raise ValueError(f"CapnoBase reference column is invalid: {column}")
    return values


def load_record(root: Path, case_id: str) -> CapnoBaseRecord:
    if not re.fullmatch(r"[0-9]{4}", case_id):
        raise ValueError("CapnoBase case identifier is invalid")
    csv_root = _csv_root(root)
    signal_path = csv_root / f"{case_id}_8min_signal.tab"
    reference_path = csv_root / f"{case_id}_8min_reference.tab"
    signal_frame = pd.read_csv(signal_path, usecols=["pleth_y"])
    reference_frame = pd.read_csv(reference_path, dtype=str, keep_default_na=False)
    ppg = signal_frame["pleth_y"].to_numpy(dtype=np.float64)
    times = _space_separated_vector(reference_frame, "rr_co2_x")
    rates = _space_separated_vector(reference_frame, "rr_co2_y")
    if ppg.size < SIGNAL_RATE_HZ * 64 or not np.isfinite(ppg).all():
        raise ValueError("CapnoBase PPG signal is invalid")
    if times.size != rates.size:
        raise ValueError("CapnoBase respiratory reference alignment is invalid")
    valid_reference = np.isfinite(times) & np.isfinite(rates) & (rates >= 4.0) & (rates <= 60.0)
    excluded = int(np.sum(~valid_reference))
    times = times[valid_reference]
    rates = rates[valid_reference]
    if times.size < 2 or np.any(np.diff(times) <= 0.0):
        raise ValueError("CapnoBase has too few references in the supported 4-60 bpm band")
    return CapnoBaseRecord(case_id, ppg, SIGNAL_RATE_HZ, times, rates, excluded)


__all__ = [
    "CapnoBaseRecord",
    "acquire_capnobase",
    "case_ids",
    "fetch_pinned_manifest",
    "load_record",
    "validate_metadata",
]
