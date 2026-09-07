"""Deterministic multimodal typed-record simulator; never patient data."""

from datetime import datetime, timedelta
from random import Random
from uuid import NAMESPACE_URL, uuid5

from app.schemas.member2 import (
    InstantReadingCreate,
    IntervalReadingCreate,
    MetricType,
    PermissionState,
    ReadingCreate,
    RecordingMethod,
    SeriesReadingCreate,
    SeriesSample,
    SessionReadingCreate,
    SessionStage,
    SourceType,
)


def _event_id(seed: int, user_id: int, time: datetime, metric: str) -> object:
    return uuid5(NAMESPACE_URL, f"sim:{seed}:{user_id}:{time.isoformat()}:{metric}")


def _common(seed: int, user_id: int, time: datetime, metric: str) -> dict[str, object]:
    return {
        "event_id": _event_id(seed, user_id, time, metric),
        "source": SourceType.SIMULATED,
        "device_id": "simulator-v2",
        "device_manufacturer": "OpenAI research fixture",
        "device_model": "deterministic-multimodal-v2",
        "device_type": "simulator",
        "recording_method": RecordingMethod.SYNTHETIC,
        "permission_state": PermissionState.UNAVAILABLE,
        "metadata": {"exclude_from_pilot": True, "seed": seed},
    }


def generate_health_feed(
    user_id: int,
    start: datetime,
    hours: int = 24,
    seed: int = 42,
) -> list[ReadingCreate]:
    if user_id <= 0:
        raise ValueError("user_id must be positive")
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must include a UTC offset")
    if not 1 <= hours <= 168:
        raise ValueError("hours must be between 1 and 168")

    rng = Random(seed)
    records: list[ReadingCreate] = []
    for hour in range(hours):
        interval_start = start + timedelta(hours=hour)
        interval_end = interval_start + timedelta(hours=1)
        steps = max(1, int(rng.gauss(450, 180)))
        base_hr = max(45.0, min(150.0, rng.gauss(68 + min(steps / 100, 18), 5)))
        samples = [
            SeriesSample(
                observed_at=interval_start + timedelta(minutes=minute),
                value=round(base_hr + rng.gauss(0, 2), 1),
            )
            for minute in (10, 25, 40, 55)
        ]
        records.append(
            SeriesReadingCreate(
                **_common(seed, user_id, interval_start, "heart_rate"),
                metric=MetricType.HEART_RATE,
                unit="bpm",
                start_at=interval_start,
                end_at=interval_end,
                samples=samples,
            )
        )
        records.append(
            IntervalReadingCreate(
                **_common(seed, user_id, interval_start, "steps"),
                metric=MetricType.STEPS,
                unit="count",
                start_at=interval_start,
                end_at=interval_end,
                value=float(steps),
            )
        )

    # One daily recovery context block at the beginning of each simulated day.
    for day in range((hours - 1) // 24 + 1):
        day_start = start + timedelta(days=day)
        if day_start >= start + timedelta(hours=hours):
            break
        records.extend(
            [
                InstantReadingCreate(
                    **_common(seed, user_id, day_start, "hrv_rmssd"),
                    metric=MetricType.HRV_RMSSD,
                    unit="ms",
                    observed_at=day_start,
                    value=round(max(5.0, rng.gauss(48, 8)), 1),
                ),
                InstantReadingCreate(
                    **_common(seed, user_id, day_start, "spo2"),
                    metric=MetricType.SPO2,
                    unit="%",
                    observed_at=day_start,
                    value=round(max(90.0, min(100.0, rng.gauss(97, 1))), 1),
                ),
                SeriesReadingCreate(
                    **_common(seed, user_id, day_start, "skin_temperature"),
                    metric=MetricType.SKIN_TEMPERATURE,
                    unit="degC_delta",
                    start_at=day_start,
                    end_at=day_start + timedelta(minutes=30),
                    samples=[
                        SeriesSample(
                            observed_at=day_start + timedelta(minutes=minute),
                            value=round(rng.gauss(0, 0.15), 2),
                        )
                        for minute in (5, 15, 25)
                    ],
                ),
                SessionReadingCreate(
                    **_common(seed, user_id, day_start, "sleep_duration"),
                    metric=MetricType.SLEEP_DURATION,
                    unit="min",
                    start_at=day_start - timedelta(hours=8),
                    end_at=day_start,
                    stages=[
                        SessionStage(
                            start_at=day_start - timedelta(hours=8),
                            end_at=day_start - timedelta(hours=7, minutes=30),
                            stage="awake_in_bed",
                        ),
                        SessionStage(
                            start_at=day_start - timedelta(hours=7, minutes=30),
                            end_at=day_start,
                            stage="sleeping",
                        ),
                    ],
                ),
            ]
        )
    return records


generate_scalar_feed = generate_health_feed
