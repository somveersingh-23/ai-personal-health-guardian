"""Reproducible participant-held-out benchmark for Member 2 sensor intelligence."""

from __future__ import annotations

import json
import platform
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sensor_intelligence.datasets import bidmc, capnobase, ppg_dalia, ptt_ppg
from sensor_intelligence.evaluation.metrics import regression_metrics
from sensor_intelligence.evaluation.splits import ParticipantSplit, participant_split
from sensor_intelligence.evaluation.windows import (
    WindowObservation,
    bidmc_windows,
    ppg_dalia_windows,
)
from sensor_intelligence.paths import require_within
from sensor_intelligence.signal_processing import (
    analyze_ppg_window,
    estimate_respiration_rate_from_impedance,
    estimate_respiration_rate_from_ppg_fusion,
    extract_paired_optical_features,
)

QUALITY_ERROR_LIMIT_BPM = 5.0
TARGET_ACCEPTED_PRECISION = 0.90


def _input_provenance(dataset_root: Path, dataset: str, version: str) -> dict[str, Any]:
    data_directory = dataset_root.parents[2]
    manifest = data_directory / "manifests" / f"{dataset}-{version}.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"dataset provenance manifest is missing: {manifest}")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("dataset") != dataset or payload.get("version") != version:
        raise ValueError("dataset provenance manifest does not match benchmark input")
    return {
        "dataset": payload["dataset"],
        "version": payload["version"],
        "homepage": payload["homepage"],
        "retrieved_at": payload["retrieved_at"],
        "resources": [
            {
                "name": item["name"],
                "bytes": item["bytes"],
                "sha256": item["sha256"],
                "publisher_md5": item.get("publisher_md5"),
                "publisher_checksums_verified": item.get(
                    "publisher_checksums_verified", 0
                ),
                "nested_archives": [
                    {
                        "path": nested["path"],
                        "sha256": nested["sha256"],
                        "members": nested["members"],
                        "uncompressed_bytes": nested["uncompressed_bytes"],
                    }
                    for nested in item.get("nested_archives", [])
                ],
            }
            for item in payload["resources"]
        ],
    }


def _observations(
    dataset: str,
    root: Path,
    participants: list[str],
    max_windows_per_participant: int | None,
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    failed_windows = 0
    for participant in participants:
        if dataset == "ppg-dalia":
            record = ppg_dalia.load_record(root, participant)
            windows = ppg_dalia_windows(record)
        elif dataset == "bidmc":
            record = bidmc.load_record(root, participant)
            windows = bidmc_windows(record)
        else:
            raise ValueError(f"unsupported benchmark dataset: {dataset}")
        if max_windows_per_participant is not None:
            windows = windows[:max_windows_per_participant]
        for window in windows:
            try:
                row = _analyze(window)
            except ValueError:
                failed_windows += 1
                continue
            rows.append(row)
    if not rows:
        raise ValueError(f"no usable {dataset} windows were produced")
    return rows, failed_windows


def _analyze(window: WindowObservation) -> dict[str, Any]:
    features = analyze_ppg_window(
        window.ppg,
        window.ppg_rate_hz,
        window.acceleration,
        window.acceleration_rate_hz,
    )
    error = abs(features.estimated_heart_rate_bpm - window.reference_heart_rate_bpm)
    return {
        "participant_id": window.participant_id,
        "window_index": window.window_index,
        "activity_id": window.activity_id,
        "reference_heart_rate_bpm": window.reference_heart_rate_bpm,
        "estimated_heart_rate_bpm": features.estimated_heart_rate_bpm,
        "quality_target": int(error <= QUALITY_ERROR_LIMIT_BPM),
        **features.model_features(),
    }


def _feature_names(rows: list[dict[str, Any]]) -> list[str]:
    excluded = {
        "participant_id",
        "window_index",
        "reference_heart_rate_bpm",
        "estimated_heart_rate_bpm",
        "quality_target",
        "activity_id",
    }
    return sorted(set(rows[0]) - excluded)


def _matrix(
    rows: list[dict[str, Any]], participants: tuple[str, ...], feature_names: list[str]
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    selected = [row for row in rows if row["participant_id"] in participants]
    if not selected:
        raise ValueError("participant split produced no windows")
    features = np.asarray([[row[name] for name in feature_names] for row in selected], dtype=float)
    labels = np.asarray([row["quality_target"] for row in selected], dtype=int)
    return features, labels, selected


def _select_threshold(labels: np.ndarray, probabilities: np.ndarray) -> float:
    candidates = np.unique(np.concatenate(([0.0, 1.0], probabilities)))
    best_feasible: tuple[float, float] | None = None
    best_fallback = (float("-inf"), 0.5)
    for threshold in candidates:
        accepted = probabilities >= threshold
        coverage = float(np.mean(accepted))
        precision = float(np.mean(labels[accepted])) if accepted.any() else 0.0
        if precision >= TARGET_ACCEPTED_PRECISION and (
            best_feasible is None or coverage > best_feasible[0]
        ):
            best_feasible = (coverage, float(threshold))
        predictions = accepted.astype(int)
        score = balanced_accuracy_score(labels, predictions)
        if score > best_fallback[0]:
            best_fallback = (float(score), float(threshold))
    return best_feasible[1] if best_feasible else best_fallback[1]


def _classification_metrics(
    labels: np.ndarray, probabilities: np.ndarray, threshold: float
) -> dict[str, float | int | None]:
    accepted = probabilities >= threshold
    predictions = accepted.astype(int)
    bin_edges = np.linspace(0.0, 1.0, 11)
    expected_calibration_error = 0.0
    for left, right in zip(bin_edges[:-1], bin_edges[1:], strict=True):
        in_bin = (probabilities >= left) & (
            (probabilities <= right) if right == 1.0 else (probabilities < right)
        )
        if in_bin.any():
            expected_calibration_error += float(np.mean(in_bin)) * abs(
                float(np.mean(probabilities[in_bin])) - float(np.mean(labels[in_bin]))
            )
    result: dict[str, float | int | None] = {
        "windows": int(labels.size),
        "quality_prevalence": float(np.mean(labels)),
        "acceptance_coverage": float(np.mean(accepted)),
        "accepted_precision": float(precision_score(labels, predictions, zero_division=0)),
        "good_window_recall": float(recall_score(labels, predictions, zero_division=0)),
        "bad_window_recall_specificity": float(
            recall_score(labels, predictions, pos_label=0, zero_division=0)
        ),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "expected_calibration_error_10_bin": expected_calibration_error,
        "roc_auc": None,
        "average_precision": None,
    }
    if np.unique(labels).size == 2:
        result["roc_auc"] = float(roc_auc_score(labels, probabilities))
        result["average_precision"] = float(average_precision_score(labels, probabilities))
    return result


def _error_report(rows: list[dict[str, Any]], accepted: np.ndarray | None = None) -> dict[str, Any]:
    selected = (
        rows
        if accepted is None
        else [row for row, keep in zip(rows, accepted, strict=True) if keep]
    )
    if not selected:
        return {"windows": 0}
    return regression_metrics(
        [row["reference_heart_rate_bpm"] for row in selected],
        [row["estimated_heart_rate_bpm"] for row in selected],
    )


def _participant_error_report(
    rows: list[dict[str, Any]],
    participants: tuple[str, ...],
    accepted: np.ndarray | None = None,
) -> dict[str, Any]:
    per_participant: dict[str, dict[str, Any]] = {}
    maes: list[float] = []
    rmses: list[float] = []
    within_5s: list[float] = []

    for p in participants:
        indices = np.asarray([row["participant_id"] == p for row in rows], dtype=bool)
        p_rows = [row for row, keep in zip(rows, indices, strict=True) if keep]
        p_accepted = None if accepted is None else accepted[indices]
        metrics = _error_report(p_rows, p_accepted)
        per_participant[p] = metrics
        if metrics.get("windows", 0) > 0:
            if "mae_bpm" in metrics:
                maes.append(float(metrics["mae_bpm"]))
            if "rmse_bpm" in metrics:
                rmses.append(float(metrics["rmse_bpm"]))
            if "within_5_bpm_fraction" in metrics:
                within_5s.append(float(metrics["within_5_bpm_fraction"]))

    return {
        "overall": _error_report(rows, accepted),
        "per_participant": per_participant,
        "participant_macro_summary": {
            "participants": len(per_participant),
            "macro_mean_mae_bpm": float(np.mean(maes)) if maes else None,
            "macro_mean_rmse_bpm": float(np.mean(rmses)) if rmses else None,
            "macro_mean_within_5_bpm_fraction": float(np.mean(within_5s)) if within_5s else None,
        },
    }


def _activity_report(
    rows: list[dict[str, Any]], accepted: np.ndarray
) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    activities = sorted(
        {int(row["activity_id"]) for row in rows if row["activity_id"] is not None}
    )
    for activity in activities:
        indices = np.asarray([row["activity_id"] == activity for row in rows], dtype=bool)
        activity_rows = [row for row, keep in zip(rows, indices, strict=True) if keep]
        activity_accepted = accepted[indices]
        report[str(activity)] = {
            "all_windows": _error_report(activity_rows),
            "acceptance_coverage": float(np.mean(activity_accepted)),
            "accepted_windows": _error_report(activity_rows, activity_accepted),
        }
    return report


def _serialize_model(
    model: Pipeline, feature_names: list[str], threshold: float
) -> dict[str, Any]:
    imputer = model.named_steps["imputer"]
    scaler = model.named_steps["scaler"]
    classifier = model.named_steps["classifier"]
    return {
        "format": "transparent-logistic-regression-v1",
        "feature_names": feature_names,
        "imputer_statistics": imputer.statistics_.astype(float).tolist(),
        "scaler_mean": scaler.mean_.astype(float).tolist(),
        "scaler_scale": scaler.scale_.astype(float).tolist(),
        "classifier_coefficients": classifier.coef_[0].astype(float).tolist(),
        "classifier_intercept": float(classifier.intercept_[0]),
        "acceptance_threshold": threshold,
        "quality_target_definition": f"absolute pulse-rate error <= {QUALITY_ERROR_LIMIT_BPM} bpm",
        "intended_use": "research signal-usability gating only; not diagnosis",
    }


def _bidmc_respiration_report(
    dataset_root: Path, participants: tuple[str, ...]
) -> dict[str, Any]:
    reference_values: list[float] = []
    ppg_estimates: list[float] = []
    impedance_estimates: list[float] = []
    component_agreement: list[bool] = []
    participant_values: dict[str, dict[str, list[float]]] = {
        participant: {"reference": [], "estimate": [], "agreement": []}
        for participant in participants
    }
    failed_windows = 0
    window_seconds = 64.0
    stride_seconds = 8.0
    for participant in participants:
        record = bidmc.load_record(dataset_root, participant)
        ppg = record.channel("ppg")
        respiration = record.channel("respiration")
        width = int(window_seconds * ppg.sampling_rate_hz)
        stride = int(stride_seconds * ppg.sampling_rate_hz)
        for start in range(0, ppg.values.size - width + 1, stride):
            end = start + width
            annotator_rates: list[float] = []
            for annotation in record.annotations.values():
                indices = annotation.sample_indices
                in_window = indices[(indices >= start) & (indices < end)]
                if in_window.size >= 4:
                    intervals = np.diff(in_window) / annotation.sampling_rate_hz
                    annotator_rates.append(float(60.0 / np.median(intervals)))
            if len(annotator_rates) != 2:
                failed_windows += 1
                continue
            try:
                ppg_result = estimate_respiration_rate_from_ppg_fusion(
                    ppg.values[start:end], ppg.sampling_rate_hz
                )
                impedance_rate = estimate_respiration_rate_from_impedance(
                    respiration.values[start:end], respiration.sampling_rate_hz
                )
            except ValueError:
                failed_windows += 1
                continue
            reference = float(np.mean(annotator_rates))
            reference_values.append(reference)
            ppg_estimates.append(ppg_result.rate_bpm)
            impedance_estimates.append(impedance_rate)
            component_agreement.append(ppg_result.components_agree)
            participant_values[participant]["reference"].append(reference)
            participant_values[participant]["estimate"].append(ppg_result.rate_bpm)
            participant_values[participant]["agreement"].append(
                float(ppg_result.components_agree)
            )
    if not reference_values:
        raise ValueError("no BIDMC manual-breath respiration windows were produced")
    agreement_array = np.asarray(component_agreement, dtype=bool)
    participant_report: dict[str, Any] = {}
    for participant, values in participant_values.items():
        participant_agreement = np.asarray(values["agreement"], dtype=bool)
        participant_report[participant] = {
            "all_windows": regression_metrics(values["reference"], values["estimate"]),
            "component_agreement_coverage": float(np.mean(participant_agreement)),
            "component_agreement_windows": (
                regression_metrics(
                    np.asarray(values["reference"])[participant_agreement],
                    np.asarray(values["estimate"])[participant_agreement],
                )
                if participant_agreement.any()
                else None
            ),
        }
    return {
        "window_protocol": {"window_seconds": window_seconds, "stride_seconds": stride_seconds},
        "reference": "mean of two manual annotator median inter-breath rates",
        "failed_windows": failed_windows,
        "ppg_multimodulation_fusion": regression_metrics(
            reference_values, ppg_estimates
        ),
        "ppg_component_agreement_coverage": float(np.mean(agreement_array)),
        "ppg_component_agreement_windows": (
            regression_metrics(
                np.asarray(reference_values)[agreement_array],
                np.asarray(ppg_estimates)[agreement_array],
            )
            if agreement_array.any()
            else None
        ),
        "participant_breakdown": participant_report,
        "impedance_respiration_sanity": regression_metrics(
            reference_values, impedance_estimates
        ),
    }


def run_ppg_dalia_benchmark(
    dataset_root: Path,
    output_root: Path,
    max_windows_per_participant: int | None = None,
) -> dict[str, Any]:
    participants = ppg_dalia.participant_ids(dataset_root)
    split = participant_split(participants)
    rows, failed_windows = _observations(
        "ppg-dalia", dataset_root, participants, max_windows_per_participant
    )
    feature_names = _feature_names(rows)
    train_x, train_y, train_rows = _matrix(rows, split.train, feature_names)
    validation_x, validation_y, validation_rows = _matrix(rows, split.validation, feature_names)
    test_x, test_y, test_rows = _matrix(rows, split.test, feature_names)
    if np.unique(train_y).size < 2:
        raise ValueError("training data must contain both usable and unusable windows")

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced", max_iter=2_000, random_state=20260829
                ),
            ),
        ]
    )
    model.fit(train_x, train_y)
    validation_probability = model.predict_proba(validation_x)[:, 1]
    threshold = _select_threshold(validation_y, validation_probability)
    test_probability = model.predict_proba(test_x)[:, 1]
    accepted = test_probability >= threshold

    test_summary = ", ".join(split.test)
    report: dict[str, Any] = {
        "schema_version": "1.2.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": "ppg-dalia",
        "input_provenance": _input_provenance(dataset_root, "ppg-dalia", "1.0"),
        "purpose": "participant-held-out pulse-rate and signal-usability research validation",
        "non_diagnostic": True,
        "scientific_disclosures_and_limitations": {
            "correlated_overlapping_windows": (
                "Windows are generated with 8-second duration and 2-second stride (75% overlap). "
                "Adjacent windows exhibit strong serial correlation. Standard IID assumptions and "
                "naive window-level bootstrap confidence intervals are statistically invalid."
            ),
            "test_split_sample_size": (
                f"Held-out test split contains {len(split.test)} participants ({test_summary}). "
                "While strictly separated without data leakage, 3 participants cannot capture the "
                "full spectrum of skin tones, motion dynamics, arrhythmias, or variability."
            ),
            "production_boundary": (
                "Research/signal-usability gate only. The model is NOT in production backend "
                "and is never used for medical diagnosis or emergency triage."
            ),
            "ppg_respiration_status": (
                "PPG respiration is implemented as auditable baseline/amplitude/frequency "
                "fusion. Component agreement is only a reported diagnostic, not a validated "
                "acceptance gate; the estimate remains research-only."
            ),
            "spo2_status": (
                "Dual-wavelength SpO2 feature extraction and calibration gating are implemented "
                "separately; this single-channel dataset cannot validate them."
            ),
        },
        "window_protocol": {"window_seconds": 8, "stride_seconds": 2},
        "quality_target_error_limit_bpm": QUALITY_ERROR_LIMIT_BPM,
        "split": asdict(split),
        "failed_windows": failed_windows,
        "all_windows": len(rows),
        "baseline": {
            "train": _error_report(train_rows),
            "validation": _error_report(validation_rows),
            "test": _error_report(test_rows),
            "test_participant_breakdown": _participant_error_report(test_rows, split.test),
        },
        "quality_gate": {
            "threshold_selected_on_validation_only": threshold,
            "validation": _classification_metrics(
                validation_y, validation_probability, threshold
            ),
            "test": _classification_metrics(test_y, test_probability, threshold),
            "accepted_test_pulse_rate": _error_report(test_rows, accepted),
            "accepted_test_participant_breakdown": _participant_error_report(
                test_rows, split.test, accepted
            ),
            "test_by_activity_id": _activity_report(test_rows, accepted),
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = require_within(output_root, output_root / "ppg-dalia-benchmark.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    model_root = dataset_root.parents[3] / "ml" / "models"
    model_root.mkdir(parents=True, exist_ok=True)
    model_path = require_within(model_root, model_root / "ppg-quality-model.json")
    model_artifact = _serialize_model(model, feature_names, threshold)
    model_artifact.update(
        {
            "trained_at": report["generated_at"],
            "training_dataset": report["input_provenance"],
            "participant_split": report["split"],
            "held_out_test_metrics": report["quality_gate"]["test"],
        }
    )
    model_path.write_text(
        json.dumps(model_artifact, indent=2), encoding="utf-8"
    )
    return report


def run_bidmc_external_benchmark(
    dataset_root: Path,
    output_root: Path,
    max_windows_per_participant: int | None = None,
) -> dict[str, Any]:
    participants = bidmc.participant_ids(dataset_root)
    split: ParticipantSplit = participant_split(participants)
    rows, failed_windows = _observations(
        "bidmc", dataset_root, participants, max_windows_per_participant
    )
    test_rows = [row for row in rows if row["participant_id"] in split.test]
    report = {
        "schema_version": "1.2.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": "bidmc",
        "input_provenance": _input_provenance(dataset_root, "bidmc", "1.0.0"),
        "purpose": "untuned external-domain PPG pulse-rate sanity benchmark",
        "non_diagnostic": True,
        "domain_warning": (
            "short critical-care pulse-oximeter recordings are not consumer-wearable validation"
        ),
        "scientific_disclosures_and_limitations": {
            "correlated_overlapping_windows": (
                "Windows are generated with 8-second duration and 2-second stride (75% overlap). "
                "Adjacent windows exhibit strong serial correlation. Confidence intervals omitted."
            ),
            "test_split_sample_size": (
                f"Held-out external test split contains {len(split.test)} participants."
            ),
            "production_boundary": "External research domain sanity test only.",
            "ppg_respiration_status": (
                "PPG multimodulation fusion is evaluated below. Component agreement did not "
                "improve BIDMC error and is not used as an acceptance gate."
            ),
            "spo2_status": (
                "Dual-wavelength feature extraction is implemented, but BIDMC cannot validate "
                "SpO2 because it has only one PPG waveform."
            ),
        },
        "window_protocol": {"window_seconds": 8, "stride_seconds": 2},
        "split": asdict(split),
        "failed_windows": failed_windows,
        "held_out_test_pulse_rate": _error_report(test_rows),
        "held_out_test_participant_breakdown": _participant_error_report(test_rows, split.test),
        "held_out_test_respiration_rate": _bidmc_respiration_report(
            dataset_root, split.test
        ),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = require_within(output_root, output_root / "bidmc-external-benchmark.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def run_capnobase_external_respiration_benchmark(
    dataset_root: Path,
    output_root: Path,
    max_windows_per_participant: int | None = None,
) -> dict[str, Any]:
    """Evaluate the frozen PPG-RR estimator on benchmark-only CapnoBase records."""

    case_reports: dict[str, Any] = {}
    references: list[float] = []
    estimates: list[float] = []
    component_agreement: list[bool] = []
    failed_windows = 0
    excluded_reference_points = 0
    window_seconds = 64.0
    stride_seconds = 8.0
    width = int(window_seconds * capnobase.SIGNAL_RATE_HZ)
    stride = int(stride_seconds * capnobase.SIGNAL_RATE_HZ)

    for case_id in capnobase.case_ids(dataset_root):
        record = capnobase.load_record(dataset_root, case_id)
        excluded_reference_points += record.excluded_reference_points
        case_references: list[float] = []
        case_estimates: list[float] = []
        case_agreement: list[bool] = []
        starts = list(range(0, record.ppg.size - width + 1, stride))
        if max_windows_per_participant is not None:
            starts = starts[:max_windows_per_participant]
        for start in starts:
            end = start + width
            start_seconds = start / record.ppg_rate_hz
            end_seconds = end / record.ppg_rate_hz
            reference_mask = (
                (record.reference_times_seconds >= start_seconds)
                & (record.reference_times_seconds < end_seconds)
            )
            if int(np.sum(reference_mask)) < 3:
                failed_windows += 1
                continue
            try:
                result = estimate_respiration_rate_from_ppg_fusion(
                    record.ppg[start:end], record.ppg_rate_hz
                )
            except ValueError:
                failed_windows += 1
                continue
            reference = float(np.median(record.reference_respiration_bpm[reference_mask]))
            references.append(reference)
            estimates.append(result.rate_bpm)
            component_agreement.append(result.components_agree)
            case_references.append(reference)
            case_estimates.append(result.rate_bpm)
            case_agreement.append(result.components_agree)
        metrics = regression_metrics(case_references, case_estimates)
        agreement = np.asarray(case_agreement, dtype=bool)
        case_reports[case_id] = {
            "all_windows": metrics,
            "component_agreement_coverage": float(np.mean(agreement)),
            "component_agreement_windows": (
                regression_metrics(
                    np.asarray(case_references)[agreement],
                    np.asarray(case_estimates)[agreement],
                )
                if agreement.any()
                else None
            ),
        }

    if not references:
        raise ValueError("no usable CapnoBase respiratory-rate windows were produced")
    agreement_array = np.asarray(component_agreement, dtype=bool)
    case_maes = [float(item["all_windows"]["mae_bpm"]) for item in case_reports.values()]
    case_within_5 = [
        float(item["all_windows"]["within_5_bpm_fraction"])
        for item in case_reports.values()
    ]
    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": "capnobase",
        "input_provenance": _input_provenance(dataset_root, "capnobase", "1.1"),
        "purpose": "frozen, untuned external PPG respiratory-rate benchmark",
        "non_diagnostic": True,
        "benchmark_integrity": (
            "Algorithm and window protocol were frozen before this dataset was evaluated; "
            "CapnoBase was not used for training, threshold selection or tuning."
        ),
        "window_protocol": {
            "window_seconds": window_seconds,
            "stride_seconds": stride_seconds,
            "reference": "median CapnoBase capnography respiratory rate within each window",
        },
        "failed_windows": failed_windows,
        "excluded_reference_points": excluded_reference_points,
        "all_windows": regression_metrics(references, estimates),
        "component_agreement_coverage": float(np.mean(agreement_array)),
        "component_agreement_windows": (
            regression_metrics(
                np.asarray(references)[agreement_array],
                np.asarray(estimates)[agreement_array],
            )
            if agreement_array.any()
            else None
        ),
        "case_breakdown": case_reports,
        "case_macro_summary": {
            "cases": len(case_reports),
            "macro_mean_mae_bpm": float(np.mean(case_maes)),
            "macro_mean_within_5_bpm_fraction": float(np.mean(case_within_5)),
        },
        "scientific_limitations": (
            "Anaesthesia-domain data do not establish wrist-wearable or clinical performance; "
            "overlapping windows are serially correlated and no IID confidence interval is used. "
            "Non-finite or out-of-supported-band (4-60 bpm) reference points are excluded and "
            "counted above."
        ),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = require_within(output_root, output_root / "capnobase-rr-benchmark.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _dual_wavelength_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [row for row in rows if row["usable"]]
    rejection_counts: Counter[str] = Counter()
    for row in rows:
        rejection_counts.update(row["rejection_reasons"])

    def distribution(key: str) -> dict[str, float] | None:
        values = np.asarray([row[key] for row in usable], dtype=float)
        if not values.size:
            return None
        return {
            "median": float(np.median(values)),
            "p05": float(np.percentile(values, 5)),
            "p95": float(np.percentile(values, 95)),
        }

    return {
        "windows": len(rows),
        "usable_windows": len(usable),
        "usable_coverage": len(usable) / len(rows) if rows else 0.0,
        "rejection_reason_counts": dict(sorted(rejection_counts.items())),
        "usable_channel_1_to_2_ratio": distribution("channel_1_to_2_ratio"),
        "usable_channel_1_perfusion_index_percent": distribution(
            "channel_1_perfusion_index_percent"
        ),
        "usable_channel_2_perfusion_index_percent": distribution(
            "channel_2_perfusion_index_percent"
        ),
        "usable_pulse_correlation": distribution("pulse_correlation"),
        "usable_spectral_concentration": distribution("spectral_concentration"),
    }


def run_ptt_ppg_dual_wavelength_validation(
    dataset_root: Path,
    output_root: Path,
    max_windows_per_participant: int | None = None,
) -> dict[str, Any]:
    """Validate paired optical signal plumbing without assuming wavelength order."""

    rows: list[dict[str, Any]] = []
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    spot_spo2: list[float] = []
    failed_windows = 0
    window_seconds = 8.0
    stride_seconds = 8.0
    records = ptt_ppg.record_names(dataset_root)
    participants: set[str] = set()
    for record_name in records:
        record = ptt_ppg.load_record(dataset_root, record_name)
        participants.add(record.participant_id)
        spot_spo2.extend((record.spo2_start_percent, record.spo2_end_percent))
        width = int(window_seconds * record.sampling_rate_hz)
        stride = int(stride_seconds * record.sampling_rate_hz)
        starts = list(range(0, record.distal_channel_1.size - width + 1, stride))
        if max_windows_per_participant is not None:
            starts = starts[:max_windows_per_participant]
        positions = {
            "distal": (record.distal_channel_1, record.distal_channel_2),
            "proximal": (record.proximal_channel_1, record.proximal_channel_2),
        }
        for position, (channel_1, channel_2) in positions.items():
            for start in starts:
                end = start + width
                try:
                    features = extract_paired_optical_features(
                        channel_1[start:end], channel_2[start:end], record.sampling_rate_hz
                    )
                except ValueError:
                    failed_windows += 1
                    continue
                row = {
                    "record": record_name,
                    "participant": record.participant_id,
                    "activity": record.activity,
                    "position": position,
                    "usable": features.usable,
                    "rejection_reasons": features.rejection_reasons,
                    "channel_1_to_2_ratio": features.ratio_of_ratios,
                    "channel_1_perfusion_index_percent": (
                        features.channel_1_perfusion_index_percent
                    ),
                    "channel_2_perfusion_index_percent": (
                        features.channel_2_perfusion_index_percent
                    ),
                    "pulse_correlation": features.pulse_correlation,
                    "spectral_concentration": features.spectral_concentration,
                }
                rows.append(row)
                grouped[f"activity:{record.activity}"].append(row)
                grouped[f"position:{position}"].append(row)

    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": "ptt-ppg",
        "input_provenance": _input_provenance(dataset_root, "ptt-ppg", "1.1.0"),
        "purpose": "real paired optical PPG signal-path and feature validation",
        "non_diagnostic": True,
        "records": len(records),
        "participants": len(participants),
        "window_protocol": {
            "window_seconds": window_seconds,
            "stride_seconds": stride_seconds,
            "positions": ["distal", "proximal"],
        },
        "publisher_channel_mapping_conflict": {
            "status": "unresolved_blocking_calibration",
            "hardware_section": "pleth_1/4 infrared; pleth_2/5 red",
            "data_description_section": "pleth_1/4 red; pleth_2/5 infrared",
            "report_convention": (
                "Wavelength-neutral channel_1/channel_2 names; ratio orientation is descriptive "
                "only and must not be used for calibration."
            ),
        },
        "failed_windows": failed_windows,
        "overall": _dual_wavelength_summary(rows),
        "breakdown": {
            key: _dual_wavelength_summary(value) for key, value in sorted(grouped.items())
        },
        "spot_spo2_metadata": {
            "values": len(spot_spo2),
            "minimum_percent": float(np.min(spot_spo2)),
            "maximum_percent": float(np.max(spot_spo2)),
            "use_for_calibration": False,
            "reason": (
                "Only boundary spot checks are available; they are not synchronized continuous "
                "arterial-reference labels and cover a narrow healthy range."
            ),
        },
        "calibration": {
            "device_specific_calibration_available": False,
            "spo2_values_emitted": 0,
            "behavior": "abstain_with_device_calibration_required",
        },
        "scientific_limitations": (
            "This validates paired-channel acquisition, optical ratio features and abstention. "
            "The publisher's conflicting wavelength mapping prevents wavelength-specific use. "
            "It does not validate SpO2 accuracy, hypoxaemia performance or medical use."
        ),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = require_within(output_root, output_root / "ptt-ppg-signal-validation.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
