"""In-memory research records with explicit sampling/provenance."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class SignalChannel:
    name: str
    values: FloatArray
    sampling_rate_hz: float
    unit: str

    def __post_init__(self) -> None:
        if self.values.ndim != 1 or self.values.size == 0:
            raise ValueError(f"{self.name} must be a non-empty one-dimensional channel")
        if not np.isfinite(self.values).all():
            raise ValueError(f"{self.name} contains non-finite values")
        if self.sampling_rate_hz <= 0:
            raise ValueError("sampling rate must be positive")


@dataclass(frozen=True, slots=True)
class EventAnnotation:
    name: str
    sample_indices: NDArray[np.int64]
    sampling_rate_hz: float

    def __post_init__(self) -> None:
        if self.sample_indices.ndim != 1 or self.sample_indices.size == 0:
            raise ValueError(f"{self.name} must contain one-dimensional sample indices")
        if np.any(self.sample_indices < 0) or np.any(np.diff(self.sample_indices) <= 0):
            raise ValueError(f"{self.name} sample indices must be non-negative and increasing")
        if self.sampling_rate_hz <= 0:
            raise ValueError("annotation sampling rate must be positive")


@dataclass(frozen=True, slots=True)
class ResearchRecord:
    dataset: str
    participant_id: str
    duration_seconds: float
    channels: dict[str, SignalChannel]
    references: dict[str, SignalChannel] = field(default_factory=dict)
    annotations: dict[str, EventAnnotation] = field(default_factory=dict)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def channel(self, name: str) -> SignalChannel:
        try:
            return self.channels[name]
        except KeyError as exc:
            raise KeyError(f"{self.dataset}/{self.participant_id} has no channel {name!r}") from exc
