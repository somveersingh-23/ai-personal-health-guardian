"""Immutable consent receipts with explicit withdrawal lifecycle."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ConsentReceipt(Base):
    __tablename__ = "consent_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose_version: Mapped[str] = mapped_column(String(64), nullable=False)
    notice_version: Mapped[str] = mapped_column(String(64), nullable=False)
    granted_metrics_json: Mapped[list] = mapped_column(JSON, nullable=False)
    granted_sources_json: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (Index("ix_consent_user_status", "user_id", "status"),)


__all__ = ["ConsentReceipt"]
