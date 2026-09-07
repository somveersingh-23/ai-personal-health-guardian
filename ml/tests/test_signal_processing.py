from __future__ import annotations

import numpy as np

from sensor_intelligence.signal_processing.ppg import analyze_ppg_window
from sensor_intelligence.signal_processing.respiration import (
    estimate_respiration_rate_from_impedance,
    estimate_respiration_rate_from_ppg,
    estimate_respiration_rate_from_ppg_fusion,
)
from sensor_intelligence.signal_processing.spo2 import (
    QuadraticSpO2Calibration,
    estimate_spo2,
    extract_dual_wavelength_features,
    extract_paired_optical_features,
)


def test_ppg_estimator_recovers_known_pulse_rate() -> None:
    sampling_rate = 64.0
    seconds = 8.0
    time = np.arange(int(sampling_rate * seconds)) / sampling_rate
    frequency = 72.0 / 60.0
    ppg = np.sin(2 * np.pi * frequency * time) + 0.18 * np.sin(
        4 * np.pi * frequency * time
    )

    result = analyze_ppg_window(ppg, sampling_rate)

    assert abs(result.estimated_heart_rate_bpm - 72.0) < 2.0
    assert 0.0 <= result.spectral_entropy <= 1.0
    assert result.autocorrelation_strength > 0.5


def test_ppg_estimator_adds_motion_features() -> None:
    ppg_rate = 64.0
    acceleration_rate = 32.0
    ppg_time = np.arange(512) / ppg_rate
    acceleration_time = np.arange(256) / acceleration_rate
    ppg = np.sin(2 * np.pi * 1.25 * ppg_time)
    acceleration = np.sin(2 * np.pi * 2.0 * acceleration_time)

    result = analyze_ppg_window(ppg, ppg_rate, acceleration, acceleration_rate)

    assert result.motion_rms > 0
    assert 0.0 <= result.ppg_motion_correlation <= 1.0


def test_respiration_estimators_recover_known_modulation() -> None:
    sampling_rate = 125.0
    time = np.arange(int(32 * sampling_rate)) / sampling_rate
    respiratory_frequency = 18.0 / 60.0
    respiration = np.sin(2 * np.pi * respiratory_frequency * time)
    ppg = (1.0 + 0.25 * respiration) * np.sin(2 * np.pi * 1.2 * time)

    impedance_rate = estimate_respiration_rate_from_impedance(respiration, sampling_rate)
    ppg_rate = estimate_respiration_rate_from_ppg(ppg, sampling_rate)

    assert abs(impedance_rate - 18.0) < 1.0
    assert abs(ppg_rate - 18.0) < 1.0


def test_ppg_respiration_fusion_exposes_components_and_agreement() -> None:
    sampling_rate = 125.0
    time = np.arange(int(64 * sampling_rate)) / sampling_rate
    breathing = np.sin(2 * np.pi * (15.0 / 60.0) * time)
    phase = 2 * np.pi * 1.25 * time + 0.12 * breathing
    ppg = 0.08 * breathing + (1.0 + 0.20 * breathing) * np.sin(phase)

    result = estimate_respiration_rate_from_ppg_fusion(ppg, sampling_rate)

    assert abs(result.rate_bpm - 15.0) < 1.0
    assert result.components_agree
    assert result.window_seconds == 64.0
    assert result.component_spread_bpm <= 4.0


def test_spo2_requires_explicit_device_calibration() -> None:
    sampling_rate = 100.0
    time = np.arange(int(10 * sampling_rate)) / sampling_rate
    pulse = np.sin(2 * np.pi * 1.2 * time)
    red = 1_000.0 + 10.0 * pulse
    infrared = 1_000.0 + 20.0 * pulse

    result = estimate_spo2(red, infrared, sampling_rate, calibration=None)

    assert not result.accepted
    assert result.reason == "device_calibration_required"
    assert result.features.usable
    assert np.isclose(result.features.ratio_of_ratios, 0.5)


def test_spo2_applies_only_the_supplied_calibration() -> None:
    sampling_rate = 100.0
    time = np.arange(int(10 * sampling_rate)) / sampling_rate
    pulse = np.sin(2 * np.pi * 1.2 * time)
    red = 1_000.0 + 10.0 * pulse
    infrared = 1_000.0 + 20.0 * pulse
    calibration = QuadraticSpO2Calibration(
        model_id="fixture-calibration-v1",
        device_family="synthetic-test-sensor",
        coefficient_quadratic=0.0,
        coefficient_linear=-10.0,
        intercept=100.0,
        minimum_ratio=0.4,
        maximum_ratio=1.2,
    )

    result = estimate_spo2(red, infrared, sampling_rate, calibration)

    assert result.accepted
    assert np.isclose(result.value_percent, 95.0)
    assert result.calibration_model_id == "fixture-calibration-v1"


def test_spo2_calibration_owns_device_specific_ratio_range() -> None:
    sampling_rate = 100.0
    time = np.arange(int(10 * sampling_rate)) / sampling_rate
    pulse = np.sin(2 * np.pi * 1.2 * time)
    red = 1_000.0 + 40.0 * pulse
    infrared = 1_000.0 + 10.0 * pulse
    calibration = QuadraticSpO2Calibration(
        model_id="fixture-calibration-v1",
        device_family="synthetic-test-sensor",
        coefficient_quadratic=0.0,
        coefficient_linear=-10.0,
        intercept=100.0,
        minimum_ratio=0.4,
        maximum_ratio=1.2,
    )

    result = estimate_spo2(red, infrared, sampling_rate, calibration)

    assert result.features.usable
    assert np.isclose(result.features.ratio_of_ratios, 4.0)
    assert not result.accepted
    assert result.reason == "ratio is outside this device calibration range"


def test_spo2_rejects_flat_or_unsynchronized_channels() -> None:
    sampling_rate = 100.0
    flat = np.full(int(10 * sampling_rate), 1_000.0)

    features = extract_dual_wavelength_features(flat, flat, sampling_rate)

    assert not features.usable
    assert "insufficient_perfusion" in features.rejection_reasons

    with np.testing.assert_raises_regex(ValueError, "equal length"):
        extract_dual_wavelength_features(flat, flat[:-1], sampling_rate)


def test_paired_optical_extractor_does_not_assume_wavelength_order() -> None:
    sampling_rate = 100.0
    time = np.arange(int(10 * sampling_rate)) / sampling_rate
    pulse = np.sin(2 * np.pi * 1.2 * time)

    features = extract_paired_optical_features(
        1_000.0 + 10.0 * pulse,
        1_000.0 + 20.0 * pulse,
        sampling_rate,
    )

    assert features.usable
    assert np.isclose(features.ratio_of_ratios, 0.5)
    assert features.channel_1_perfusion_index_percent < (
        features.channel_2_perfusion_index_percent
    )
