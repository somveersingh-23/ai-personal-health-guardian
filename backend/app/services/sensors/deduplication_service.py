"""Deterministic request-scoped deduplication; the database remains authoritative."""

from app.schemas.member2 import ReadingCreate


def source_identity(reading: ReadingCreate, user_id: int) -> tuple[int, str, str, str] | None:
    if reading.source_record_id is None:
        return None
    origin = reading.data_origin_package or reading.source.value
    record_type = reading.source_record_type or f"{reading.metric.value}:{reading.temporal_type.value}"
    return user_id, origin, record_type, reading.source_record_id


def deduplicate_batch(
    readings: list[ReadingCreate],
    user_id: int,
) -> tuple[list[ReadingCreate], list[ReadingCreate]]:
    seen_event_ids: set[object] = set()
    seen_source_records: set[tuple[int, str, str, str]] = set()
    unique: list[ReadingCreate] = []
    duplicates: list[ReadingCreate] = []
    for reading in readings:
        identity = source_identity(reading, user_id)
        if reading.event_id in seen_event_ids or (identity is not None and identity in seen_source_records):
            duplicates.append(reading)
            continue
        seen_event_ids.add(reading.event_id)
        if identity is not None:
            seen_source_records.add(identity)
        unique.append(reading)
    return unique, duplicates
