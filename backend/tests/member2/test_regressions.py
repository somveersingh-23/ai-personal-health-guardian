"""Regression cases found by the source and scientific-contract audit."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.models.member2 import HealthEvent, SensorCollectionState
from app.schemas.member2 import (
    HealthEventBatchCreate,
    MetricType,
    ReadingCreate,
    ReconciliationSessionCreate,
    SourceDeletionRequest,
)
from app.services.sensors import normalize_reading, fuse_events
from app.services.sensors.persistence_service import (
    persist_batch,
    delete_source_records,
    purge_member2_data,
    event_from_orm,
)
from app.services.sensors.reconciliation_service import (
    begin_reconciliation,
    complete_reconciliation,
)
from app.services.sensors.transactions import CollectionPausedError, resume_collection

NOW = datetime(2026, 1, 15, 12, tzinfo=UTC)


def reading(**overrides):
    payload = dict(
        event_id=str(uuid4()),
        metric="resting_heart_rate",
        temporal_type="instant",
        unit="bpm",
        source="health_connect",
        observed_at=NOW,
        value=62,
        data_origin_package="com.example.watch",
        source_record_type="RestingHeartRateRecord",
        source_record_id="record-1",
        source_last_modified_at=NOW,
        device_id="watch-1",
        device_type="watch",
        recording_method="automatically_recorded",
        permission_state="granted_foreground",
        wear_state="worn",
        motion_state="still",
    )
    payload.update(overrides)
    if payload["temporal_type"] != "instant":
        payload.pop("observed_at")
    if payload["temporal_type"] in {"session", "series"}:
        payload.pop("value")
    return TypeAdapter(ReadingCreate).validate_python(payload)


def batch(*items):
    return HealthEventBatchCreate(events=list(items))


def vector(*items, metrics=None):
    events = [normalize_reading(item, 7, NOW) for item in items]
    return fuse_events(
        events,
        metrics or list(dict.fromkeys(e.metric for e in events)),
        NOW - timedelta(hours=1),
        NOW + timedelta(minutes=1),
    )


@pytest.mark.parametrize(
    "stage,minutes", [("awake", 0), ("deep", 60), ("out_of_bed", 0)]
)
def test_sleep_uses_stage_semantics(stage, minutes):
    item = reading(
        metric="sleep_duration",
        temporal_type="session",
        unit="min",
        source_record_type="SleepSessionRecord",
        start_at=NOW - timedelta(hours=1),
        end_at=NOW,
        stages=[dict(stage=stage, start_at=NOW - timedelta(hours=1), end_at=NOW)],
    )
    assert vector(item).features[0].value == minutes


def test_sleep_without_stages_does_not_claim_time_asleep():
    item = reading(
        metric="sleep_duration",
        temporal_type="session",
        unit="min",
        source_record_type="SleepSessionRecord",
        start_at=NOW - timedelta(hours=1),
        end_at=NOW,
        stages=[],
    )
    assert vector(item).abstained


def test_absolute_and_delta_temperature_are_not_averaged():
    common = dict(
        metric="skin_temperature",
        temporal_type="series",
        source_record_type="SkinTemperatureRecord",
        start_at=NOW - timedelta(minutes=1),
        end_at=NOW,
    )
    absolute = reading(
        **common,
        source="wearable_bluetooth",
        unit="degC",
        samples=[dict(observed_at=NOW - timedelta(seconds=30), value=34)],
    )
    delta = reading(
        **common,
        unit="degC_delta",
        source_record_id="delta",
        samples=[dict(observed_at=NOW - timedelta(seconds=30), value=1)],
    )
    result = vector(absolute, delta)
    assert result.abstained
    assert "skin_temperature:incompatible_units" in result.contradictions


def test_totally_motion_corrupted_metric_cannot_be_rescued_by_good_other_metric():
    bad = reading(value=190, motion_artifact_score=1.0)
    good = reading(
        metric="spo2",
        unit="%",
        value=98,
        source_record_type="OxygenSaturationRecord",
        source_record_id="spo2",
    )
    result = vector(bad, good)
    assert MetricType.RESTING_HEART_RATE in result.missing_metrics
    assert all(item.metric != MetricType.RESTING_HEART_RATE for item in result.features)


def test_series_with_no_samples_inside_window_is_missing():
    # An overlapping record is not evidence unless its samples overlap too.
    item = reading(
        metric="heart_rate",
        temporal_type="series",
        source_record_type="HeartRateRecord",
        start_at=NOW - timedelta(hours=2),
        end_at=NOW,
        samples=[dict(observed_at=NOW - timedelta(minutes=90), value=70)],
    )
    assert vector(item).abstained


def test_conflicting_devices_do_not_produce_an_averaged_vital():
    first = reading(value=60)
    second = reading(
        value=120, device_id="other-watch", source_record_id="other-record"
    )
    result = vector(first, second)
    assert result.abstained
    assert "resting_heart_rate:source_disagreement" in result.contradictions


def test_future_source_revision_cannot_poison_update_order():
    with pytest.raises(ValueError, match="source revision time"):
        normalize_reading(reading(source_last_modified_at=NOW+timedelta(days=1)), 7, NOW)


def test_partial_cumulative_record_is_not_presented_as_an_exact_total():
    item = reading(
        metric="steps",
        temporal_type="interval",
        unit="count",
        value=1000,
        source_record_type="StepsRecord",
        start_at=NOW - timedelta(hours=2),
        end_at=NOW,
    )
    result = vector(item)
    assert result.abstained
    assert "steps:requires_source_aggregation" in result.contradictions


def test_persistence_revision_privacy_and_reconciliation(tmp_path):
    async def scenario():
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{tmp_path / 'regression.db'}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            old = reading()
            latest = reading(
                value=70, source_last_modified_at=NOW + timedelta(minutes=1)
            )
            result = await persist_batch(
                session, batch(old, latest), 7, NOW + timedelta(minutes=2)
            )
            assert (result.inserted_count, result.duplicate_count) == (1, 1)
            assert result.events[0].value == 70
            row = await session.scalar(select(HealthEvent).where(HealthEvent.user_id == 7))
            aged = event_from_orm(row, NOW+timedelta(days=2))
            assert aged.freshness_status.value == "historical"
            assert aged.data_freshness_seconds == 2*86400
            other = reading(source_record_id="other", event_id=latest.event_id)
            with pytest.raises(ValueError, match="immutable"):
                await persist_batch(
                    session, batch(other), 7, NOW + timedelta(minutes=2)
                )
            # An old deletion replay cannot delete a newer source revision.
            deletion = SourceDeletionRequest(
                source="health_connect",
                source_record_type="RestingHeartRateRecord",
                source_record_ids=["record-1"],
                deleted_at=NOW,
            )
            deletion_result = await delete_source_records(session, 7, deletion)
            assert deletion_result.deleted_count == 0
            assert deletion_result.tombstoned_count == 0
            # Snapshot started before this update must not remove that update.
            snapshot = await begin_reconciliation(
                session,
                7,
                ReconciliationSessionCreate(
                    source="health_connect",
                    source_record_type="RestingHeartRateRecord",
                    window_start=NOW - timedelta(hours=1),
                    window_end=NOW + timedelta(hours=1),
                ),
                NOW + timedelta(minutes=3),
            )
            updated = reading(
                value=75, source_last_modified_at=NOW + timedelta(minutes=4)
            )
            await persist_batch(session, batch(updated), 7, NOW + timedelta(minutes=4))
            completion = await complete_reconciliation(
                session, 7, snapshot.session_id, NOW + timedelta(minutes=5)
            )
            assert completion.tombstoned_stale_count == 0
            assert (
                await complete_reconciliation(
                    session, 7, snapshot.session_id, NOW + timedelta(minutes=6)
                )
            ).tombstoned_stale_count == 0
            # Keep another profile intact through purge.
            await persist_batch(
                session, batch(reading(source_record_id="user8")), 8, NOW
            )
            assert (await purge_member2_data(session, 7))["health_events"] == 1
            assert (await session.get(SensorCollectionState, 7)).paused
            with pytest.raises(CollectionPausedError):
                await persist_batch(session, batch(reading()), 7, NOW)
            assert (
                len(
                    list(
                        (
                            await session.scalars(
                                select(HealthEvent).where(HealthEvent.user_id == 8)
                            )
                        ).all()
                    )
                )
                == 1
            )
            await resume_collection(session, 7)
            assert (
                await persist_batch(session, batch(reading()), 7, NOW)
            ).inserted_count == 1
        await engine.dispose()

    asyncio.run(scenario())
