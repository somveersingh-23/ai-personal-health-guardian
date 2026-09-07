"""Deterministic request-scoped deduplication; the database remains authoritative."""

from app.schemas.member2 import ReadingCreate
from datetime import UTC, datetime


def source_identity(
    reading: ReadingCreate, user_id: int
) -> tuple[int, str, str, str] | None:
    if reading.source_record_id is None:
        return None
    origin = reading.data_origin_package or reading.source.value
    record_type = (
        reading.source_record_type
        or f"{reading.metric.value}:{reading.temporal_type.value}"
    )
    return user_id, origin, record_type, reading.source_record_id


def deduplicate_batch(
    readings: list[ReadingCreate],
    user_id: int,
) -> tuple[list[ReadingCreate], list[ReadingCreate]]:
    identities = {}
    for reading in readings:
        identity = (
            source_identity(reading, user_id),
            reading.source,
            reading.metric,
            reading.temporal_type,
        )
        if reading.event_id in identities and identities[reading.event_id] != identity:
            raise ValueError("event_id cannot identify different sources or metrics")
        identities[reading.event_id] = identity
    seen = {}
    unique: list[ReadingCreate] = []
    duplicates: list[ReadingCreate] = []
    for reading in sorted(
        readings,
        key=lambda item: item.source_last_modified_at
        or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        identity = source_identity(reading, user_id)
        key = identity if identity is not None else reading.event_id
        previous = seen.get(key)
        if previous is not None:
            if (
                previous.metric != reading.metric
                or previous.temporal_type != reading.temporal_type
            ):
                raise ValueError(
                    "source identity cannot change metric or temporal type"
                )
            if (
                previous.source_last_modified_at == reading.source_last_modified_at
                and previous.model_dump(exclude={"event_id"})
                != reading.model_dump(exclude={"event_id"})
            ):
                raise ValueError("conflicting values at the same source revision")
            duplicates.append(reading)
            continue
        seen[key] = reading
        unique.append(reading)
    return unique, duplicates
