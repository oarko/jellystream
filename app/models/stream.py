"""Stream model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

from app.core.database import Base


class Stream(Base):
    """Stream configuration model."""

    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    jellyfin_library_id = Column(String(255), nullable=False)
    stream_url = Column(String(512), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
