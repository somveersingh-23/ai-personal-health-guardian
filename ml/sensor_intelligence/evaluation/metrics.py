"""Aggregate error metrics suitable for pulse-rate engineering validation."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def regression_metrics(reference: ArrayLike, estimate: ArrayLike) -> dict[str, float | int]:
    expected = np.asarray(reference, dtype=float)
    predicted = np.asarray(estimate, dtype=float)
    if expected.shape != predicted.shape or expected.ndim != 1 or expected.size == 0:
        raise ValueError("reference and estimate must be aligned non-empty vectors")
    if not np.isfinite(expected).all() or not np.isfinite(predicted).all():
        raise ValueError("metrics require finite values")
    error = predicted - expected
    absolute = np.abs(error)
    bias = float(np.mean(error))
    difference_sd = float(np.std(error, ddof=1)) if error.size > 1 else 0.0
    return {
        "windows": int(error.size),
        "mae_bpm": float(np.mean(absolute)),
        "rmse_bpm": float(np.sqrt(np.mean(np.square(error)))),
        "median_absolute_error_bpm": float(np.median(absolute)),
        "p95_absolute_error_bpm": float(np.percentile(absolute, 95)),
        "within_5_bpm_fraction": float(np.mean(absolute <= 5.0)),
        "bland_altman_bias_bpm": bias,
        "bland_altman_lower_95_bpm": bias - 1.96 * difference_sd,
        "bland_altman_upper_95_bpm": bias + 1.96 * difference_sd,
    }
