"""Motion-aware PPG features and a deliberately transparent pulse-rate baseline.

This module estimates pulse rate for engineering validation. It is not a diagnostic
algorithm and must not be used to infer a disease or oxygen saturation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import signal, stats

MIN_PULSE_BPM = 30.0
MAX_PULSE_BPM = 220.0


@dataclass(frozen=True, slots=True)
class PpgWindowFeatures:
    estimated_heart_rate_bpm: float
    spectral_snr_db: float
    spectral_entropy: float
    autocorrelation_strength: float
    peak_interval_cv: float
    skewness: float
    kurtosis: float
    flatline_fraction: float
    saturation_fraction: float
    motion_rms: float
    ppg_motion_correlation: float

    def model_features(self) -> dict[str, float]:
        payload = asdict(self)
        payload.pop("estimated_heart_rate_bpm")
        return payload


def _validated(values: NDArray[np.float64] | np.ndarray, name: str) -> NDArray[np.float64]:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size < 32:
        raise ValueError(f"{name} window is too short")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} window contains non-finite samples")
    return array


def _bandpass(values: NDArray[np.float64], sampling_rate_hz: float) -> NDArray[np.float64]:
    if sampling_rate_hz <= 2 * (MAX_PULSE_BPM / 60):
        raise ValueError("sampling rate is too low for the supported pulse band")
    centered = signal.detrend(values, type="linear")
    sos = signal.butter(
        4,
        [MIN_PULSE_BPM / 60, MAX_PULSE_BPM / 60],
        btype="bandpass",
        fs=sampling_rate_hz,
        output="sos",
    )
    return signal.sosfiltfilt(sos, centered)


def _normalized_spectrum(
    values: NDArray[np.float64], sampling_rate_hz: float, nfft: int
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    frequencies, power = signal.welch(
        values,
        fs=sampling_rate_hz,
        window="hann",
        nperseg=values.size,
        noverlap=0,
        nfft=max(nfft, values.size),
        detrend=False,
        scaling="spectrum",
    )
    return frequencies, np.maximum(power, np.finfo(np.float64).tiny)


def analyze_ppg_window(
    ppg: NDArray[np.float64] | np.ndarray,
    sampling_rate_hz: float,
    acceleration: NDArray[np.float64] | np.ndarray | None = None,
    acceleration_rate_hz: float | None = None,
) -> PpgWindowFeatures:
    """Return interpretable PPG/motion features and a spectral HR estimate."""

    raw = _validated(np.asarray(ppg), "PPG")
    filtered = _bandpass(raw, sampling_rate_hz)
    nfft = max(2048, 1 << (raw.size - 1).bit_length())
    frequencies, ppg_power = _normalized_spectrum(filtered, sampling_rate_hz, nfft)
    pulse_mask = (frequencies >= MIN_PULSE_BPM / 60) & (
        frequencies <= MAX_PULSE_BPM / 60
    )
    if not pulse_mask.any():
        raise ValueError("PPG spectrum does not contain the supported pulse band")

    pulse_power = ppg_power[pulse_mask]
    candidate_score = pulse_power / pulse_power.max()
    motion_rms = 0.0
    ppg_motion_correlation = 0.0
    if acceleration is not None:
        if acceleration_rate_hz is None or acceleration_rate_hz <= 0:
            raise ValueError("acceleration sampling rate is required")
        motion = _validated(np.asarray(acceleration), "acceleration")
        motion_centered = signal.detrend(motion, type="constant")
        motion_rms = float(np.sqrt(np.mean(np.square(motion_centered))))
        motion_frequencies, motion_power = _normalized_spectrum(
            motion_centered, acceleration_rate_hz, nfft
        )
        interpolated_motion_power = np.interp(
            frequencies[pulse_mask], motion_frequencies, motion_power
        )
        normalized_motion = interpolated_motion_power / interpolated_motion_power.max()
        candidate_score = candidate_score / (1.0 + 2.0 * normalized_motion)

        ppg_time = np.arange(filtered.size) / sampling_rate_hz
        motion_time = np.arange(motion_centered.size) / acceleration_rate_hz
        motion_at_ppg_rate = np.interp(ppg_time, motion_time, motion_centered)
        if np.std(motion_at_ppg_rate) > 0 and np.std(filtered) > 0:
            ppg_motion_correlation = float(abs(np.corrcoef(filtered, motion_at_ppg_rate)[0, 1]))

    peak_index = int(np.argmax(candidate_score))
    peak_frequency = float(frequencies[pulse_mask][peak_index])
    estimated_hr = peak_frequency * 60.0
    peak_band = np.abs(frequencies[pulse_mask] - peak_frequency) <= 0.12
    signal_power = float(pulse_power[peak_band].sum())
    noise_power = float(pulse_power[~peak_band].sum())
    spectral_snr_db = float(10.0 * np.log10(signal_power / max(noise_power, 1e-15)))

    probabilities = pulse_power / pulse_power.sum()
    spectral_entropy = float(
        -np.sum(probabilities * np.log(probabilities + 1e-15)) / np.log(probabilities.size)
    )

    autocorrelation = signal.correlate(filtered, filtered, mode="full", method="fft")
    autocorrelation = autocorrelation[filtered.size - 1 :]
    autocorrelation /= max(float(autocorrelation[0]), 1e-15)
    min_lag = max(1, int(sampling_rate_hz * 60.0 / MAX_PULSE_BPM))
    max_lag = min(autocorrelation.size, int(sampling_rate_hz * 60.0 / MIN_PULSE_BPM) + 1)
    autocorrelation_strength = float(np.max(autocorrelation[min_lag:max_lag]))

    minimum_distance = max(1, int(sampling_rate_hz * 60.0 / MAX_PULSE_BPM))
    peaks, _ = signal.find_peaks(
        filtered,
        distance=minimum_distance,
        prominence=max(float(np.std(filtered)) * 0.20, 1e-12),
    )
    intervals = np.diff(peaks) / sampling_rate_hz
    peak_interval_cv = (
        float(np.std(intervals) / np.mean(intervals)) if intervals.size >= 2 else 2.0
    )

    raw_range = float(np.ptp(raw))
    epsilon = max(raw_range * 1e-5, np.finfo(np.float64).eps)
    flatline_fraction = float(np.mean(np.abs(np.diff(raw)) <= epsilon))
    edge_tolerance = max(raw_range * 1e-6, np.finfo(np.float64).eps)
    saturation_fraction = float(
        np.mean((raw <= raw.min() + edge_tolerance) | (raw >= raw.max() - edge_tolerance))
    )

    values = {
        "estimated_heart_rate_bpm": estimated_hr,
        "spectral_snr_db": spectral_snr_db,
        "spectral_entropy": spectral_entropy,
        "autocorrelation_strength": autocorrelation_strength,
        "peak_interval_cv": peak_interval_cv,
        "skewness": float(stats.skew(filtered, bias=False)),
        "kurtosis": float(stats.kurtosis(filtered, fisher=True, bias=False)),
        "flatline_fraction": flatline_fraction,
        "saturation_fraction": saturation_fraction,
        "motion_rms": motion_rms,
        "ppg_motion_correlation": ppg_motion_correlation,
    }
    sanitized = {key: float(value) if np.isfinite(value) else 0.0 for key, value in values.items()}
    return PpgWindowFeatures(**sanitized)
