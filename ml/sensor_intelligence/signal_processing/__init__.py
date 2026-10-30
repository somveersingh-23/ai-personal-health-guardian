"""Transparent signal-processing primitives for research validation."""

from sensor_intelligence.signal_processing.ppg import PpgWindowFeatures, analyze_ppg_window
from sensor_intelligence.signal_processing.respiration import (
    PpgRespirationEstimate,
    estimate_respiration_rate_from_impedance,
    estimate_respiration_rate_from_ppg,
    estimate_respiration_rate_from_ppg_fusion,
)
from sensor_intelligence.signal_processing.spo2 import (
    DualWavelengthFeatures,
    PairedOpticalFeatures,
    QuadraticSpO2Calibration,
    SpO2Estimate,
    estimate_spo2,
    extract_dual_wavelength_features,
    extract_paired_optical_features,
)

__all__ = [
    "PpgWindowFeatures",
    "PpgRespirationEstimate",
    "DualWavelengthFeatures",
    "PairedOpticalFeatures",
    "QuadraticSpO2Calibration",
    "SpO2Estimate",
    "analyze_ppg_window",
    "estimate_respiration_rate_from_impedance",
    "estimate_respiration_rate_from_ppg",
    "estimate_respiration_rate_from_ppg_fusion",
    "estimate_spo2",
    "extract_dual_wavelength_features",
    "extract_paired_optical_features",
]
