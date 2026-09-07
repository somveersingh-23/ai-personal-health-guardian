"""Dual-wavelength PPG features and explicitly calibrated SpO2 research estimates.

Oxygen saturation cannot be inferred from a single PPG channel or from a
universal coefficient set. This module separates signal feature extraction
from device-specific calibration and abstains whenever the channels, quality,
calibration range or output range are invalid.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import signal

MIN_WINDOW_SECONDS = 8.0


@dataclass(frozen=True, slots=True)
class PairedOpticalFeatures:
    ratio_of_ratios: float | None
    channel_1_perfusion_index_percent: float
    channel_2_perfusion_index_percent: float
    pulse_correlation: float
    spectral_concentration: float
    usable: bool
    rejection_reasons: tuple[str, ...]

    @property
    def red_perfusion_index_percent(self) -> float:
        """Channel 1 perfusion when the caller has verified it is red."""

        return self.channel_1_perfusion_index_percent

    @property
    def infrared_perfusion_index_percent(self) -> float:
        """Channel 2 perfusion when the caller has verified it is infrared."""

        return self.channel_2_perfusion_index_percent


# Compatibility name for callers that already supply verified red then infrared channels.
DualWavelengthFeatures = PairedOpticalFeatures


@dataclass(frozen=True, slots=True)
class QuadraticSpO2Calibration:
    """Calibration supplied and validated for one explicit sensor configuration."""

    model_id: str
    device_family: str
    coefficient_quadratic: float
    coefficient_linear: float
    intercept: float
    minimum_ratio: float
    maximum_ratio: float
    minimum_spo2_percent: float = 70.0
    maximum_spo2_percent: float = 100.0

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.device_family.strip():
            raise ValueError("calibration identity and device family are required")
        numbers = (
            self.coefficient_quadratic,
            self.coefficient_linear,
            self.intercept,
            self.minimum_ratio,
            self.maximum_ratio,
            self.minimum_spo2_percent,
            self.maximum_spo2_percent,
        )
        if not np.isfinite(numbers).all():
            raise ValueError("calibration values must be finite")
        if self.minimum_ratio >= self.maximum_ratio:
            raise ValueError("calibration ratio range is invalid")
        if self.minimum_spo2_percent >= self.maximum_spo2_percent:
            raise ValueError("calibration SpO2 range is invalid")

    def apply(self, ratio_of_ratios: float) -> float:
        if not self.minimum_ratio <= ratio_of_ratios <= self.maximum_ratio:
            raise ValueError("ratio is outside this device calibration range")
        return float(
            self.coefficient_quadratic * ratio_of_ratios**2
            + self.coefficient_linear * ratio_of_ratios
            + self.intercept
        )


@dataclass(frozen=True, slots=True)
class SpO2Estimate:
    value_percent: float | None
    accepted: bool
    reason: str
    calibration_model_id: str | None
    features: PairedOpticalFeatures


def _channel(values: NDArray[np.float64] | np.ndarray, name: str) -> NDArray[np.float64]:
    result = np.asarray(values, dtype=np.float64).reshape(-1)
    if result.size == 0 or not np.isfinite(result).all():
        raise ValueError(f"{name} channel must be non-empty and finite")
    return result


def _pulse_band(values: NDArray[np.float64], sampling_rate_hz: float) -> NDArray[np.float64]:
    sos = signal.butter(
        4, [0.5, 4.0], btype="bandpass", fs=sampling_rate_hz, output="sos"
    )
    return signal.sosfiltfilt(sos, signal.detrend(values, type="linear"))


def _spectral_concentration(values: NDArray[np.float64], sampling_rate_hz: float) -> float:
    frequencies, power = signal.periodogram(values, fs=sampling_rate_hz, window="hann")
    pulse_band = (frequencies >= 0.5) & (frequencies <= 4.0)
    if not pulse_band.any() or float(np.sum(power[pulse_band])) <= 0.0:
        return 0.0
    band_frequencies = frequencies[pulse_band]
    band_power = power[pulse_band]
    peak_frequency = float(band_frequencies[int(np.argmax(band_power))])
    fundamental = pulse_band & (np.abs(frequencies - peak_frequency) <= 0.12)
    return float(np.sum(power[fundamental]) / np.sum(power[pulse_band]))


def extract_paired_optical_features(
    channel_1: NDArray[np.float64] | np.ndarray,
    channel_2: NDArray[np.float64] | np.ndarray,
    sampling_rate_hz: float,
) -> PairedOpticalFeatures:
    """Extract order-sensitive optical features without assuming wavelengths."""

    channel_1_values = _channel(channel_1, "channel 1")
    channel_2_values = _channel(channel_2, "channel 2")
    if channel_1_values.size != channel_2_values.size:
        raise ValueError("paired optical channels must be synchronized and equal length")
    if sampling_rate_hz < 10.0:
        raise ValueError("paired optical PPG sampling rate must be at least 10 Hz")
    if channel_1_values.size < sampling_rate_hz * MIN_WINDOW_SECONDS:
        raise ValueError(f"paired optical window must be at least {MIN_WINDOW_SECONDS:g} seconds")

    channel_1_dc = float(np.median(channel_1_values))
    channel_2_dc = float(np.median(channel_2_values))
    channel_1_pulse = _pulse_band(channel_1_values, sampling_rate_hz)
    channel_2_pulse = _pulse_band(channel_2_values, sampling_rate_hz)
    channel_1_ac = float(np.sqrt(np.mean(np.square(channel_1_pulse))))
    channel_2_ac = float(np.sqrt(np.mean(np.square(channel_2_pulse))))
    channel_1_pi = (
        100.0 * channel_1_ac / abs(channel_1_dc) if channel_1_dc != 0.0 else 0.0
    )
    channel_2_pi = (
        100.0 * channel_2_ac / abs(channel_2_dc) if channel_2_dc != 0.0 else 0.0
    )
    correlation = (
        float(abs(np.corrcoef(channel_1_pulse, channel_2_pulse)[0, 1]))
        if channel_1_ac > 0.0 and channel_2_ac > 0.0
        else 0.0
    )
    concentration = min(
        _spectral_concentration(channel_1_pulse, sampling_rate_hz),
        _spectral_concentration(channel_2_pulse, sampling_rate_hz),
    )

    reasons: list[str] = []
    if channel_1_dc <= 0.0 or channel_2_dc <= 0.0:
        reasons.append("non_positive_dc_level")
    if channel_1_pi < 0.01 or channel_2_pi < 0.01:
        reasons.append("insufficient_perfusion")
    if channel_1_pi > 20.0 or channel_2_pi > 20.0:
        reasons.append("implausible_perfusion")
    if correlation < 0.8:
        reasons.append("wavelength_pulses_disagree")
    if concentration < 0.2:
        reasons.append("low_spectral_concentration")

    ratio: float | None = None
    if channel_1_dc > 0.0 and channel_2_dc > 0.0 and channel_2_ac > 0.0:
        ratio = float(
            (channel_1_ac / channel_1_dc) / (channel_2_ac / channel_2_dc)
        )
    else:
        reasons.append("ratio_unavailable")

    return PairedOpticalFeatures(
        ratio_of_ratios=ratio,
        channel_1_perfusion_index_percent=channel_1_pi,
        channel_2_perfusion_index_percent=channel_2_pi,
        pulse_correlation=correlation,
        spectral_concentration=concentration,
        usable=not reasons,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )


def extract_dual_wavelength_features(
    red: NDArray[np.float64] | np.ndarray,
    infrared: NDArray[np.float64] | np.ndarray,
    sampling_rate_hz: float,
) -> PairedOpticalFeatures:
    """Extract features when channel order is verified as red then infrared."""

    return extract_paired_optical_features(red, infrared, sampling_rate_hz)


def estimate_spo2(
    red: NDArray[np.float64] | np.ndarray,
    infrared: NDArray[np.float64] | np.ndarray,
    sampling_rate_hz: float,
    calibration: QuadraticSpO2Calibration | None,
) -> SpO2Estimate:
    features = extract_dual_wavelength_features(red, infrared, sampling_rate_hz)
    if calibration is None:
        return SpO2Estimate(None, False, "device_calibration_required", None, features)
    if not features.usable or features.ratio_of_ratios is None:
        return SpO2Estimate(
            None,
            False,
            ",".join(features.rejection_reasons),
            calibration.model_id,
            features,
        )
    try:
        value = calibration.apply(features.ratio_of_ratios)
    except ValueError as exc:
        return SpO2Estimate(None, False, str(exc), calibration.model_id, features)
    if not calibration.minimum_spo2_percent <= value <= calibration.maximum_spo2_percent:
        return SpO2Estimate(
            None,
            False,
            "calibrated value is outside the validated SpO2 range",
            calibration.model_id,
            features,
        )
    return SpO2Estimate(value, True, "accepted_research_estimate", calibration.model_id, features)
