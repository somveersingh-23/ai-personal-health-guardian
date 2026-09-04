from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sensor_intelligence.model import load_quality_model


def _artifact(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "format": "transparent-logistic-regression-v1",
                "feature_names": ["snr", "motion"],
                "imputer_statistics": [0.0, 0.0],
                "scaler_mean": [0.0, 0.0],
                "scaler_scale": [1.0, 1.0],
                "classifier_coefficients": [2.0, -2.0],
                "classifier_intercept": 0.0,
                "acceptance_threshold": 0.5,
            }
        ),
        encoding="utf-8",
    )


def test_transparent_model_inference(tmp_path: Path) -> None:
    artifact = tmp_path / "model.json"
    _artifact(artifact)
    model = load_quality_model(artifact)

    good = model.predict({"snr": 2.0, "motion": 0.0})
    poor = model.predict({"snr": 0.0, "motion": 2.0})

    assert good.accepted is True
    assert poor.accepted is False
    assert good.usable_probability > poor.usable_probability


def test_transparent_model_rejects_dimension_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "model.json"
    _artifact(artifact)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["classifier_coefficients"] = [1.0]
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="dimensions"):
        load_quality_model(artifact)


def test_model_checksum_pins_the_exact_non_executable_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "model.json"
    _artifact(artifact)
    expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
    model = load_quality_model(artifact, expected_sha256=expected)
    assert model.model_sha256 == expected

    artifact.write_text(artifact.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        load_quality_model(artifact, expected_sha256=expected)


def test_model_loader_rejects_diagnostic_claims(tmp_path: Path) -> None:
    artifact = tmp_path / "model.json"
    _artifact(artifact)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["intended_use"] = "diagnosis of heart disease"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="diagnostic"):
        load_quality_model(artifact)


def test_checked_in_model_matches_governance_manifest() -> None:
    models = Path(__file__).parents[1] / "models"
    manifest = json.loads(
        (models / "ppg-quality-model.manifest.json").read_text(encoding="utf-8")
    )
    model = load_quality_model(
        models / manifest["artifact"],
        expected_sha256=manifest["artifact_sha256"],
    )
    assert manifest["activation_status"] == "disabled_in_production"
    assert "not diagnosis" in model.intended_use
    assert manifest["claim_class"] == "research_only"
