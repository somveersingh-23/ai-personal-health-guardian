"""Non-executable JSON quality-model loading and deterministic inference."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sensor_intelligence.signal_processing import PpgWindowFeatures


@dataclass(frozen=True, slots=True)
class QualityPrediction:
    usable_probability: float
    accepted: bool
    model_format: str
    model_sha256: str


@dataclass(frozen=True, slots=True)
class TransparentQualityModel:
    feature_names: tuple[str, ...]
    imputer_statistics: np.ndarray
    scaler_mean: np.ndarray
    scaler_scale: np.ndarray
    coefficients: np.ndarray
    intercept: float
    threshold: float
    model_format: str
    model_sha256: str
    intended_use: str

    def predict(self, features: PpgWindowFeatures | dict[str, float]) -> QualityPrediction:
        payload = features.model_features() if isinstance(features, PpgWindowFeatures) else features
        missing = [name for name in self.feature_names if name not in payload]
        if missing:
            raise ValueError(f"quality model features are missing: {', '.join(missing)}")
        values = np.asarray([payload[name] for name in self.feature_names], dtype=float)
        values = np.where(np.isfinite(values), values, self.imputer_statistics)
        scaled = (values - self.scaler_mean) / self.scaler_scale
        logit = float(np.dot(self.coefficients, scaled) + self.intercept)
        probability = float(1.0 / (1.0 + np.exp(-np.clip(logit, -40.0, 40.0))))
        return QualityPrediction(
            usable_probability=probability,
            accepted=probability >= self.threshold,
            model_format=self.model_format,
            model_sha256=self.model_sha256,
        )


def load_quality_model(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> TransparentQualityModel:
    artifact_bytes = path.read_bytes()
    artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    if expected_sha256 is not None and artifact_sha256 != expected_sha256.lower():
        raise ValueError("quality-model artifact checksum does not match the approved manifest")
    payload = json.loads(artifact_bytes.decode("utf-8"))
    if payload.get("format") != "transparent-logistic-regression-v1":
        raise ValueError("unsupported quality-model format")
    feature_names = tuple(payload["feature_names"])
    if not feature_names or len(set(feature_names)) != len(feature_names):
        raise ValueError("quality-model feature names must be unique and non-empty")
    arrays = {
        "imputer_statistics": np.asarray(payload["imputer_statistics"], dtype=float),
        "scaler_mean": np.asarray(payload["scaler_mean"], dtype=float),
        "scaler_scale": np.asarray(payload["scaler_scale"], dtype=float),
        "coefficients": np.asarray(payload["classifier_coefficients"], dtype=float),
    }
    if any(array.shape != (len(feature_names),) for array in arrays.values()):
        raise ValueError("quality-model parameter dimensions do not match features")
    if not all(np.isfinite(array).all() for array in arrays.values()):
        raise ValueError("quality-model parameters must be finite")
    if np.any(arrays["scaler_scale"] <= 0):
        raise ValueError("quality-model scaler values must be positive")
    intercept = float(payload["classifier_intercept"])
    threshold = float(payload["acceptance_threshold"])
    if not np.isfinite(intercept) or not 0.0 <= threshold <= 1.0:
        raise ValueError("quality-model intercept or threshold is invalid")
    intended_use = str(payload.get("intended_use", "research signal-usability gating only"))
    if "diagnos" in intended_use.lower() and "not diagnos" not in intended_use.lower():
        raise ValueError("quality-model artifact attempts to declare a diagnostic intended use")
    return TransparentQualityModel(
        feature_names=feature_names,
        imputer_statistics=arrays["imputer_statistics"],
        scaler_mean=arrays["scaler_mean"],
        scaler_scale=arrays["scaler_scale"],
        coefficients=arrays["coefficients"],
        intercept=intercept,
        threshold=threshold,
        model_format=payload["format"],
        model_sha256=artifact_sha256,
        intended_use=intended_use,
    )
