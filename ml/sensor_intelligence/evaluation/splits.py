"""Deterministic participant splits that prevent window-level identity leakage."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ParticipantSplit:
    train: tuple[str, ...]
    validation: tuple[str, ...]
    test: tuple[str, ...]

    def assert_disjoint(self) -> None:
        groups = [set(self.train), set(self.validation), set(self.test)]
        if any(groups[left] & groups[right] for left in range(3) for right in range(left + 1, 3)):
            raise ValueError("participant split contains leakage")


def participant_split(
    participant_ids: list[str], seed: int = 20260829
) -> ParticipantSplit:
    unique = sorted(set(participant_ids))
    if len(unique) < 5:
        raise ValueError("at least five participants are required for train/validation/test")
    shuffled = np.asarray(unique, dtype=object)
    np.random.default_rng(seed).shuffle(shuffled)
    test_count = max(1, round(len(unique) * 0.20))
    validation_count = max(1, round(len(unique) * 0.20))
    split = ParticipantSplit(
        train=tuple(sorted(shuffled[test_count + validation_count :].tolist())),
        validation=tuple(sorted(shuffled[test_count : test_count + validation_count].tolist())),
        test=tuple(sorted(shuffled[:test_count].tolist())),
    )
    split.assert_disjoint()
    return split
