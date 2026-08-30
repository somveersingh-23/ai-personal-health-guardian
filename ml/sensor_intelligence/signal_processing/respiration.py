"""Transparent respiratory-rate estimators for research validation.

The PPG estimator follows the published RRest decomposition: respiration can
modulate the pulse baseline, pulse amplitude and beat-to-beat frequency. The
three independently estimated rates are fused without using a reference label.
This is an engineering research primitive, not a clinical measurement.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import signal

MIN_RESPIRATION_BPM = 4.0
MAX_RESPIRATION_BPM = 60.0
MIN_PPG_WINDOW_SECONDS = 32.0
RESPIRATORY_RESAMPLE_RATE_HZ = 5.0
SMART_FUSION_MAX_SPREAD_BPM = 4.0


@dataclass(frozen=True, slots=True)
class PpgRespirationEstimate:
    """Auditable output from three respiratory-induced PPG variations."""

    rate_bpm: float
    baseline_rate_bpm: float
    amplitude_rate_bpm: float
    frequency_rate_bpm: float
    component_spread_bpm: float
    components_agree: bool
    window_seconds: float


def _validated(values: NDArray[np.float64] | np.ndarray, name: str) -> NDArray[np.float64]:
    result = np.asarray(values, dtype=np.float64).reshape(-1)
    if result.size == 0 or not np.isfinite(result).all():
        raise ValueError(f"{name} must be non-empty and finite")
    return result


def _respiratory_spectrum(
    modulation: NDArray[np.float64], sampling_rate_hz: float
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    frequencies, power = signal.welch(
        signal.detrend(modulation),
        fs=sampling_rate_hz,
        window="hann",
        nperseg=modulation.size,
        noverlap=0,
        nfft=max(8192, 1 << (modulation.size - 1).bit_length()),
        scaling="spectrum",
    )
    mask = (frequencies >= MIN_RESPIRATION_BPM / 60.0) & (
        frequencies <= MAX_RESPIRATION_BPM / 60.0
    )
    if not mask.any():
        raise ValueError("signal has no supported respiration band")
    return frequencies[mask], power[mask]


def _modulation_rate(
    times: NDArray[np.float64], values: NDArray[np.float64]
) -> float:
    if times.size < 12 or values.size != times.size:
        raise ValueError("respiratory modulation has too few valid pulses")
    grid = np.arange(times[0], times[-1], 1.0 / RESPIRATORY_RESAMPLE_RATE_HZ)
    if grid.size < RESPIRATORY_RESAMPLE_RATE_HZ * 16:
        raise ValueError("respiratory modulation does not span enough time")
    interpolated = np.interp(grid, times, values)
    if np.std(interpolated) <= np.finfo(float).eps:
        raise ValueError("respiratory modulation is flat")
    frequencies, power = _respiratory_spectrum(
        interpolated, RESPIRATORY_RESAMPLE_RATE_HZ
    )
    return float(frequencies[int(np.argmax(power))] * 60.0)


def _ppg_respiratory_modulations(
    ppg: NDArray[np.float64], sampling_rate_hz: float
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    detrended = signal.detrend(ppg, type="linear")
    pulse_sos = signal.butter(
        4, [0.5, 4.0], btype="bandpass", fs=sampling_rate_hz, output="sos"
    )
    pulse = signal.sosfiltfilt(pulse_sos, detrended)
    peaks, _ = signal.find_peaks(
        pulse,
        distance=max(1, int(sampling_rate_hz * 0.3)),
        prominence=max(float(np.std(pulse)) * 0.15, 1e-12),
    )
    if peaks.size < 12:
        raise ValueError("PPG window has too few detected pulses")

    times: list[float] = []
    baseline: list[float] = []
    amplitude: list[float] = []
    frequency: list[float] = []
    for first_peak, second_peak in zip(peaks[:-1], peaks[1:], strict=True):
        interval_seconds = float(second_peak - first_peak) / sampling_rate_hz
        if not 0.3 <= interval_seconds <= 2.0:
            continue
        segment = detrended[first_peak : second_peak + 1]
        trough = first_peak + int(np.argmin(segment))
        peak_value = float(detrended[first_peak])
        trough_value = float(detrended[trough])
        times.append(float(first_peak + trough) / (2.0 * sampling_rate_hz))
        baseline.append((peak_value + trough_value) / 2.0)
        amplitude.append(peak_value - trough_value)
        frequency.append(interval_seconds)

    return (
        np.asarray(times, dtype=np.float64),
        np.asarray(baseline, dtype=np.float64),
        np.asarray(amplitude, dtype=np.float64),
        np.asarray(frequency, dtype=np.float64),
    )


def estimate_respiration_rate_from_ppg_fusion(
    ppg: NDArray[np.float64] | np.ndarray, sampling_rate_hz: float
) -> PpgRespirationEstimate:
    """Estimate three PPG respiratory modulations and fuse their rates.

    ``components_agree`` reports the published smart-fusion spread rule as a
    transparent diagnostic only. It is not a validated quality gate: callers
    must validate the estimator and any acceptance policy on their exact
    device and population before exposing a measurement.
    """

    values = _validated(ppg, "PPG")
    if sampling_rate_hz <= 8.0:
        raise ValueError("sampling rate is too low for PPG pulse isolation")
    if values.size < sampling_rate_hz * MIN_PPG_WINDOW_SECONDS:
        raise ValueError(
            f"PPG respiration window must be at least {MIN_PPG_WINDOW_SECONDS:g} seconds"
        )
    times, baseline, amplitude, frequency = _ppg_respiratory_modulations(
        values, sampling_rate_hz
    )
    component_rates = np.asarray(
        [
            _modulation_rate(times, baseline),
            _modulation_rate(times, amplitude),
            _modulation_rate(times, frequency),
        ],
        dtype=np.float64,
    )
    fused_rate = float(np.median(component_rates))
    spread = float(np.std(component_rates))
    return PpgRespirationEstimate(
        rate_bpm=fused_rate,
        baseline_rate_bpm=float(component_rates[0]),
        amplitude_rate_bpm=float(component_rates[1]),
        frequency_rate_bpm=float(component_rates[2]),
        component_spread_bpm=spread,
        components_agree=spread <= SMART_FUSION_MAX_SPREAD_BPM,
        window_seconds=float(values.size / sampling_rate_hz),
    )


def estimate_respiration_rate_from_ppg(
    ppg: NDArray[np.float64] | np.ndarray, sampling_rate_hz: float
) -> float:
    """Backward-compatible research estimate; inspect fusion quality in new code."""

    return estimate_respiration_rate_from_ppg_fusion(ppg, sampling_rate_hz).rate_bpm


def estimate_respiration_rate_from_impedance(
    respiration: NDArray[np.float64] | np.ndarray, sampling_rate_hz: float
) -> float:
    values = _validated(respiration, "respiration")
    if values.size < sampling_rate_hz * 16:
        raise ValueError("respiration window must be at least 16 seconds")
    frequencies, power = _respiratory_spectrum(values, sampling_rate_hz)
    return float(frequencies[int(np.argmax(power))] * 60.0)
