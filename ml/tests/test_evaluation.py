from __future__ import annotations

import numpy as np

from sensor_intelligence.datasets.records import EventAnnotation, ResearchRecord, SignalChannel
from sensor_intelligence.evaluation.benchmark import (
    _participant_error_report,
    _select_threshold,
)
from sensor_intelligence.evaluation.metrics import regression_metrics
from sensor_intelligence.evaluation.splits import participant_split
from sensor_intelligence.evaluation.windows import wrist_exercise_windows


def test_participant_split_is_complete_deterministic_and_disjoint() -> None:
    participants = [f"S{index}" for index in range(1, 16)]
    first = participant_split(participants)
    second = participant_split(participants)

    assert first == second
    first.assert_disjoint()
    assert set(first.train + first.validation + first.test) == set(participants)
    assert (len(first.train), len(first.validation), len(first.test)) == (9, 3, 3)


def test_regression_metrics_have_expected_units() -> None:
    result = regression_metrics([60.0, 70.0, 80.0], [61.0, 68.0, 83.0])

    assert result["windows"] == 3
    assert result["mae_bpm"] == 2.0
    assert result["within_5_bpm_fraction"] == 1.0


def test_threshold_selection_prefers_high_precision_with_maximum_coverage() -> None:
    labels = np.asarray([0, 0, 1, 1, 1])
    probabilities = np.asarray([0.1, 0.2, 0.4, 0.8, 0.9])

    threshold = _select_threshold(labels, probabilities)

    assert threshold == 0.4


def test_participant_error_report_preserves_individuals_and_macro_mean() -> None:
    rows = [
        {
            "participant_id": "P1",
            "reference_heart_rate_bpm": 60.0,
            "estimated_heart_rate_bpm": 61.0,
        },
        {
            "participant_id": "P1",
            "reference_heart_rate_bpm": 70.0,
            "estimated_heart_rate_bpm": 73.0,
        },
        {
            "participant_id": "P2",
            "reference_heart_rate_bpm": 80.0,
            "estimated_heart_rate_bpm": 90.0,
        },
    ]

    report = _participant_error_report(rows, ("P1", "P2"))

    assert set(report["per_participant"]) == {"P1", "P2"}
    assert report["per_participant"]["P1"]["mae_bpm"] == 2.0
    assert report["per_participant"]["P2"]["mae_bpm"] == 10.0
    assert report["participant_macro_summary"]["participants"] == 2
    assert report["participant_macro_summary"]["macro_mean_mae_bpm"] == 6.0


def test_wrist_windows_use_only_contemporaneous_ecg_reference_peaks() -> None:
    rate = 100.0
    samples = 2_000
    record = ResearchRecord(
        dataset="wrist-exercise",
        participant_id="s1_walk",
        duration_seconds=samples / rate,
        channels={
            "ppg": SignalChannel("ppg", np.sin(np.arange(samples)), rate, "a.u."),
            "acceleration_magnitude": SignalChannel(
                "acceleration_magnitude", np.ones(samples), rate, "a.u."
            ),
        },
        annotations={
            "ecg_r_peaks": EventAnnotation(
                "ecg_r_peaks", np.arange(50, samples, 100, dtype=np.int64), rate
            )
        },
    )

    windows = wrist_exercise_windows(record)

    assert windows
    assert windows[0].reference_heart_rate_bpm == 60.0
    assert windows[0].acceleration is not None
