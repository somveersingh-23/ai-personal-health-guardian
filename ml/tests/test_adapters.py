from __future__ import annotations

import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from app.schemas.member2.health_event import ReadingCreate
from pydantic import TypeAdapter

from sensor_intelligence.datasets import bidmc, capnobase, ppg_dalia, ptt_ppg, sleep_edf


def test_bidmc_csv_adapter_and_contract(tmp_path: Path) -> None:
    csv_root = tmp_path / "extracted" / "bidmc_csv"
    csv_root.mkdir(parents=True)
    samples = 125 * 10
    time = np.arange(samples) / 125.0
    pd.DataFrame(
        {
            "Time [s]": time,
            "PLETH": np.sin(2 * np.pi * 1.2 * time),
            "RESP": np.sin(2 * np.pi * 0.25 * time),
            "II": np.sin(2 * np.pi * 1.2 * time),
        }
    ).to_csv(csv_root / "bidmc_01_Signals.csv", index=False)
    pd.DataFrame(
        {
            "Time [s]": np.arange(10),
            "HR": [72] * 10,
            "PULSE": [72] * 10,
            "RESP": [15] * 10,
            "SpO2": [98] * 10,
        }
    ).to_csv(csv_root / "bidmc_01_Numerics.csv", index=False)
    pd.DataFrame(
        {
            "breaths ann1 [signal sample no]": [100, 500, 900],
            "breaths ann2 [signal sample no]": [105, 505, 905],
        }
    ).to_csv(csv_root / "bidmc_01_Breaths.csv", index=False)

    record = bidmc.load_record(tmp_path, "01")
    events = bidmc.to_health_events(record)
    adapter = TypeAdapter(ReadingCreate)

    assert record.channel("ppg").sampling_rate_hz == 125.0
    assert len(events) == 21
    assert all(adapter.validate_python(event) for event in events)


def test_capnobase_adapter_parses_publisher_csv_shape(tmp_path: Path) -> None:
    csv_root = tmp_path / "data" / "csv"
    csv_root.mkdir(parents=True)
    samples = int(capnobase.SIGNAL_RATE_HZ * 64)
    time = np.arange(samples) / capnobase.SIGNAL_RATE_HZ
    pd.DataFrame(
        {
            "co2_y": np.sin(2 * np.pi * 0.25 * time),
            "pleth_y": np.sin(2 * np.pi * 1.2 * time),
            "ecg_y": np.sin(2 * np.pi * 1.2 * time),
        }
    ).to_csv(csv_root / "0001_8min_signal.tab", index=False)
    pd.DataFrame(
        {
            "rr_co2_x": [" 10 20 30 40 50"],
            "rr_co2_y": [" 15 15 16 16 15"],
        }
    ).to_csv(csv_root / "0001_8min_reference.tab", index=False)

    record = capnobase.load_record(tmp_path, "0001")

    assert record.ppg_rate_hz == 300.0
    assert record.ppg.size == samples
    assert record.reference_respiration_bpm.tolist() == [15.0, 15.0, 16.0, 16.0, 15.0]
    assert record.excluded_reference_points == 0


def test_capnobase_manifest_requires_complete_pinned_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib
    import json

    files = []
    for case in range(capnobase.EXPECTED_CASE_COUNT):
        for kind in ("reference", "signal"):
            files.append(
                {
                    "label": f"{case:04d}_8min_{kind}.tab",
                    "directoryLabel": "data/csv",
                    "dataFile": {
                        "id": case * 2 + (kind == "signal") + 1,
                        "filesize": 100,
                        "checksum": {"type": "MD5", "value": "0" * 32},
                    },
                }
            )
    payload = {
        "versionNumber": 1,
        "versionMinorNumber": 1,
        "versionState": "RELEASED",
        "files": files,
    }
    canonical = capnobase._canonical_file_manifest(payload)
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    monkeypatch.setattr(capnobase, "EXPECTED_MANIFEST_SHA256", digest)

    assert len(capnobase.validate_metadata(payload)) == capnobase.EXPECTED_FILE_COUNT

    payload["files"].pop()
    with pytest.raises(ValueError, match="file count changed"):
        capnobase.validate_metadata(payload)


def test_ptt_ppg_adapter_preserves_publisher_channel_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeRecord:
        fs = 500.0
        sig_name = ["pleth_1", "pleth_2", "pleth_4", "pleth_5"]
        p_signal = np.column_stack(
            [
                np.full(4_000, 101.0),
                np.full(4_000, 202.0),
                np.full(4_000, 303.0),
                np.full(4_000, 404.0),
            ]
        )

    monkeypatch.setattr(ptt_ppg.wfdb, "rdrecord", lambda _: FakeRecord())
    csv_root = tmp_path / "csv"
    csv_root.mkdir()
    pd.DataFrame(
        {"record": ["s1_sit"], "spo2_start": [98], "spo2_end": [97]}
    ).to_csv(csv_root / "subjects_info.csv", index=False)

    record = ptt_ppg.load_record(tmp_path, "s1_sit")

    assert record.distal_channel_1[0] == 101.0
    assert record.distal_channel_2[0] == 202.0
    assert record.proximal_channel_1[0] == 303.0
    assert record.proximal_channel_2[0] == 404.0
    assert record.spo2_start_percent == 98.0


def test_ppg_dalia_restricted_loader_and_contract(tmp_path: Path) -> None:
    participant = tmp_path / "S1"
    participant.mkdir()
    payload = {
        "signal": {
            "wrist": {
                "BVP": np.linspace(-1.0, 1.0, 512).reshape(-1, 1),
                "ACC": np.ones((256, 3)),
                "TEMP": np.linspace(31.0, 32.0, 32).reshape(-1, 1),
            }
        },
        "label": np.asarray([70.0, 71.0, 72.0, 73.0]),
        "activity": np.ones(32),
    }
    with (participant / "S1.pkl").open("wb") as handle:
        pickle.dump(payload, handle, protocol=4)

    record = ppg_dalia.load_record(tmp_path, "S1")
    events = ppg_dalia.to_health_events(record)
    adapter = TypeAdapter(ReadingCreate)

    assert record.channel("acceleration").values.shape == (256,)
    assert record.channel("activity").sampling_rate_hz == 4.0
    assert len(events) == 2
    assert all(adapter.validate_python(event) for event in events)


def test_ppg_dalia_restricted_loader_rejects_arbitrary_globals(tmp_path: Path) -> None:
    class Unsafe:
        def __reduce__(self) -> tuple[object, tuple[str]]:
            return (eval, ("1 + 1",))

    payload = tmp_path / "unsafe.pkl"
    with payload.open("wb") as handle:
        pickle.dump({"unsafe": Unsafe()}, handle)

    with pytest.raises(pickle.UnpicklingError, match="forbidden"):
        ppg_dalia.restricted_load(payload)


def test_sleep_edf_adapter_merges_stages_and_validates_psg_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeEdfReader:
        def __init__(self, path: str) -> None:
            self.path = Path(path)
            self.file_duration = 300.0

        def getStartdatetime(self) -> datetime:
            return datetime(2020, 1, 1)

        def readAnnotations(self) -> tuple[list[float], list[float], list[str]]:
            return (
                [0.0, 30.0, 60.0, 90.0, 120.0],
                [30.0, 30.0, 30.0, 30.0, 30.0],
                [
                    "Sleep stage W",
                    "Sleep stage 1",
                    "Sleep stage 2",
                    "Movement time",
                    "Sleep stage R",
                ],
            )

        def close(self) -> None:
            pass

    monkeypatch.setattr(sleep_edf.pyedflib, "EdfReader", FakeEdfReader)
    hypnogram = tmp_path / "SC4001EC-Hypnogram.edf"
    psg = tmp_path / "SC4001E0-PSG.edf"

    event = sleep_edf.load_expert_session(hypnogram, psg)
    validated = TypeAdapter(ReadingCreate).validate_python(event)

    assert validated.metric.value == "sleep_duration"
    assert [stage.stage for stage in validated.stages] == ["light", "rem"]
    assert event["metadata"]["psg_pair_validated"] is True
    assert event["metadata"]["merged_stages"] == 2
