"""Minimal collection preference retained when observations are purged."""

from sqlalchemy import Boolean, Column, Integer
from app.database.base import Base


class SensorCollectionState(Base):
    __tablename__ = "sensor_collection_states"
    user_id = Column(Integer, primary_key=True)
    paused = Column(Boolean, nullable=False, default=False)
