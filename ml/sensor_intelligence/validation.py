"""Validate research adapters against the production Member 2 Pydantic contract."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from sensor_intelligence.datasets import bidmc, ppg_dalia, sleep_edf
from sensor_intelligence.paths import REPOSITORY_ROOT


def _reading_adapter() -> TypeAdapter[Any]:
    backend = str(REPOSITORY_ROOT / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from app.schemas.member2.health_event import ReadingCreate

    return TypeAdapter(ReadingCreate)


def validate_dataset_contracts(dataset: str, dataset_root: Path) -> dict[str, Any]:
    adapter = _reading_adapter()
    metric_counts: Counter[str] = Counter()
    event_count = 0
    participants = 0
    if dataset == "bidmc":
        identifiers = bidmc.participant_ids(dataset_root)
        for identifier in identifiers:
            participants += 1
            for event in bidmc.to_health_events(bidmc.load_record(dataset_root, identifier)):
                validated = adapter.validate_python(event)
                metric_counts[validated.metric.value] += 1
                event_count += 1
    elif dataset == "ppg-dalia":
        identifiers = ppg_dalia.participant_ids(dataset_root)
        for identifier in identifiers:
            participants += 1
            for event in ppg_dalia.to_health_events(
                ppg_dalia.load_record(dataset_root, identifier)
            ):
                validated = adapter.validate_python(event)
                metric_counts[validated.metric.value] += 1
                event_count += 1
    elif dataset == "sleep-edf":
        candidates = sorted(dataset_root.rglob("*-Hypnogram.edf"))
        if not candidates:
            raise FileNotFoundError(f"Sleep-EDF hypnogram not found below {dataset_root}")
        for candidate in candidates:
            matching_psg = sorted(dataset_root.rglob(f"{candidate.name[:6]}*-PSG.edf"))
            if len(matching_psg) != 1:
                raise FileNotFoundError(
                    f"expected one PSG pair for Sleep-EDF hypnogram {candidate.name}"
                )
            participants += 1
            validated = adapter.validate_python(
                sleep_edf.load_expert_session(candidate, matching_psg[0])
            )
            metric_counts[validated.metric.value] += 1
            event_count += 1
    else:
        raise ValueError(f"unsupported contract-validation dataset: {dataset}")
    return {
        "dataset": dataset,
        "participants_or_recordings": participants,
        "events": event_count,
        "metrics": dict(sorted(metric_counts.items())),
        "production_contract": "member2-health-event-v2",
        "valid": True,
    }
