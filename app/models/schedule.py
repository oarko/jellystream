"""Schedule model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Schedule(Base):
    """Schedule model for stream programming."""

    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), nullable=False)
    title = Column(String(255), nullable=False)
    media_item_id = Column(String(255), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)  # Duration in seconds
    extra_metadata = Column(Text, nullable=True)  # JSON metadata
    created_at = Column(DateTime, server_default=func.now())
