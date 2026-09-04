"""Durable staged reconciliation sessions for histories of arbitrary size."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReconciliationSession(Base):
    __tablename__ = "reconciliation_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_type: Mapped[str] = mapped_column(String(128), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="collecting")
    received_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tombstoned_stale_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_reconciliation_user_status", "user_id", "status"),)


class ReconciliationRecord(Base):
    __tablename__ = "reconciliation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reconciliation_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_record_id: Mapped[str] = mapped_column(String(256), nullable=False)

    __table_args__ = (
        Index(
            "uq_reconciliation_session_record",
            "session_id",
            "source_record_id",
            unique=True,
        ),
    )


__all__ = ["ReconciliationRecord", "ReconciliationSession"]
