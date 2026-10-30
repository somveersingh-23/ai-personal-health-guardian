from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Member3Base(DeclarativeBase):
    pass


class Member3GuardianRecord(Member3Base):
    """Durable JSON envelope for versioned Member 3 domain records."""

    __tablename__ = "member3_guardian_records"
    __table_args__ = (
        UniqueConstraint("record_type", "record_id", name="uq_member3_record"),
        Index("ix_member3_user_type", "user_id", "record_type"),
        Index("ix_member3_secondary", "record_type", "user_id", "secondary_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_type: Mapped[str] = mapped_column(String(32), nullable=False)
    record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    secondary_key: Mapped[str | None] = mapped_column(String(256))
    metadata_value: Mapped[str | None] = mapped_column(String(512))
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
