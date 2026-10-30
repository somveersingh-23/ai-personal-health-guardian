"""Receipts and device calibration must not become self-certified measurements."""

import asyncio
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database.base import Base
from app.models.member2 import DeviceCapability, DeviceRegistry
from app.schemas.member2 import (
    ConsentReceiptCreate,
    ConsentWithdrawalRequest,
    DeviceCapabilityUpsertRequest,
    HealthEventBatchCreate,
    InstantReadingCreate,
)
from app.services.sensors import normalize_reading
from app.services.sensors.governance_service import (
    create_consent_receipt,
    withdraw_consent,
)
from app.services.sensors.capability_service import (
    upsert_device_capabilities,
    enrich_event_with_device_capability,
)
from app.services.sensors.persistence_service import persist_batch


def test_receipt_timezone_idempotency_and_withdrawal_blocks_replay(tmp_path):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'consent.db'}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC) - timedelta(minutes=1)
        async with sessions() as session:
            receipt = ConsentReceiptCreate(
                purpose="sensor_intelligence_wellness",
                purpose_version="v1",
                notice_version="v1",
                granted_metrics=["resting_heart_rate"],
                granted_sources=["health_connect"],
                consented_at=now,
            )
            first = await create_consent_receipt(session, 7, receipt)
            other_offset = receipt.model_copy(
                update={
                    "consented_at": now.astimezone(
                        timezone(timedelta(hours=5, minutes=30))
                    )
                }
            )
            assert (
                await create_consent_receipt(session, 7, other_offset)
            ).id == first.id
            event = InstantReadingCreate(
                schema_version="3.0.0",
                metric="resting_heart_rate",
                unit="bpm",
                value=60,
                source="health_connect",
                observed_at=now,
                source_last_modified_at=now,
                data_origin_package="com.example.watch",
                source_record_type="RestingHeartRateRecord",
                source_record_id="consent-test",
                recording_method="automatically_recorded",
                permission_state="granted_foreground",
                consent_receipt_id=receipt.receipt_id,
                purpose_version="v1",
            )
            assert (
                await persist_batch(
                    session,
                    HealthEventBatchCreate(schema_version="3.0.0", events=[event]),
                    7,
                )
            ).inserted_count == 1
            await withdraw_consent(
                session, 7, receipt.receipt_id, ConsentWithdrawalRequest()
            )
            with pytest.raises(ValueError, match="consent is not active"):
                await persist_batch(
                    session,
                    HealthEventBatchCreate(schema_version="3.0.0", events=[event]),
                    7,
                )
            # Changing to legacy v2 cannot resurrect the withdrawn source record.
            legacy = event.model_copy(
                update={
                    "schema_version": "2.0.0",
                    "consent_receipt_id": None,
                    "purpose_version": None,
                    "source_last_modified_at": datetime.now(UTC),
                }
            )
            assert (
                await persist_batch(session, HealthEventBatchCreate(events=[legacy]), 7)
            ).inserted_count == 0
        await engine.dispose()

    asyncio.run(scenario())


def test_client_cannot_unblock_registry_and_expired_calibration_is_rejected(tmp_path):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'device.db'}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        async with sessions() as session:
            session.add(
                DeviceRegistry(
                    user_id=7, device_id="watch", source_type="health_connect"
                )
            )
            capability = DeviceCapability(
                user_id=7,
                device_id="watch",
                metric="resting_heart_rate",
                source_record_type="RestingHeartRateRecord",
                source_type="health_connect",
                support_status="blocked",
                canonical_unit_ucum="{beats}/min",
                calibration_status="unverified",
                recording_methods_json=[],
                known_limitations_json=[],
            )
            session.add(capability)
            await session.commit()
            request = DeviceCapabilityUpsertRequest(
                device_id="watch",
                capabilities=[
                    dict(
                        metric="resting_heart_rate",
                        source_record_type="RestingHeartRateRecord",
                        source_type="health_connect",
                        canonical_unit_ucum="{beats}/min",
                    )
                ],
            )
            with pytest.raises(ValueError, match="server-managed"):
                await upsert_device_capabilities(session, 7, request)
            await session.refresh(capability)
            capability.support_status = "supported"
            capability.calibration_status = "valid"
            capability.calibration_valid_until = now - timedelta(days=1)
            capability.reference_method = "test reference"
            capability.validation_protocol_version = "test-v1"
            await session.commit()
            item = InstantReadingCreate(
                metric="resting_heart_rate",
                unit="bpm",
                value=60,
                source="health_connect",
                observed_at=now,
                source_last_modified_at=now,
                data_origin_package="com.example.watch",
                source_record_type="RestingHeartRateRecord",
                source_record_id="cal-test",
                device_id="watch",
                recording_method="automatically_recorded",
                permission_state="granted_foreground",
            )
            event = await enrich_event_with_device_capability(
                session, normalize_reading(item, 7, now)
            )
            assert event.quality_vector.decision.value == "rejected"
            assert "device_calibration_expired" in event.quality_vector.reason_codes
        await engine.dispose()

    asyncio.run(scenario())
