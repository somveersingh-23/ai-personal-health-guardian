from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    height_cm: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    weight_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    known_conditions: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    medications: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    allergies: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )