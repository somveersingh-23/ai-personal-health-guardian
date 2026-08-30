"""Validate privacy-safe Member 2 physical-device evidence records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "test_id",
    "platform",
    "os_version",
    "manufacturer",
    "model",
    "source",
    "scenario",
    "app_build",
    "tested_at",
    "result",
    "evidence_reference",
    "operational_metrics",
}
ALLOWED_RESULTS = {"pending", "passed", "failed", "blocked"}
FORBIDDEN_KEYS = {
    "access_token",
    "changes_token",
    "raw_health_values",
    "raw_payload",
    "waveform",
    "camera_frame",
    "participant_name",
    "email",
}


def _walk(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_KEYS.intersection(value)
        if forbidden:
            raise ValueError(f"{path} contains forbidden sensitive keys: {sorted(forbidden)}")
        for key, nested in value.items():
            _walk(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _walk(nested, f"{path}[{index}]")


def validate(path: Path, *, require_complete: bool = False) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0.0":
        raise ValueError("device evidence requires schema_version 1.0.0")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("device evidence must contain at least one record")
    _walk(payload)
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {index} must be an object")
        missing = REQUIRED_FIELDS.difference(record)
        if missing:
            raise ValueError(f"record {index} is missing fields: {sorted(missing)}")
        test_id = record["test_id"]
        if not isinstance(test_id, str) or not test_id.strip() or test_id in seen:
            raise ValueError("test_id values must be non-empty and unique")
        seen.add(test_id)
        if record["result"] not in ALLOWED_RESULTS:
            raise ValueError(f"record {test_id} has an invalid result")
        if require_complete and record["result"] != "passed":
            raise ValueError(f"release evidence is incomplete: {test_id}={record['result']}")
        metrics = record["operational_metrics"]
        if not isinstance(metrics, dict):
            raise ValueError(f"record {test_id} operational_metrics must be an object")
        if any(value is not None and not isinstance(value, (int, float)) for value in metrics.values()):
            raise ValueError(f"record {test_id} operational metrics must be numeric or null")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    count = validate(args.path, require_complete=args.require_complete)
    print(f"Validated {count} privacy-safe device evidence record(s).")


if __name__ == "__main__":
    main()
