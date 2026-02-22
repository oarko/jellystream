"""Channel model — represents a virtual TV channel."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Channel(Base):
    """
    A virtual TV channel with scheduled programming.

    Channels are backed by one or more Jellyfin libraries and can be
    configured with genre filters for automatic schedule generation.
    """

    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    channel_number = Column(String(10), nullable=True)   # e.g. "100.1"
    enabled = Column(Boolean, default=True)

    # "video" — sources from movies/tvshows libraries (default)
    # "music" — sources from music libraries (planned, not yet active)
    channel_type = Column(String(20), default="video", nullable=False)

    # "manual"     — user manually adds schedule entries
    # "genre_auto" — auto-generated from library + genre filters
    schedule_type = Column(String(20), default="genre_auto", nullable=False)

    # Jellyfin Live TV registration IDs (set after registering with Jellyfin)
    tuner_host_id = Column(String(255), nullable=True)
    listing_provider_id = Column(String(255), nullable=True)

    # Tracks how far ahead the schedule has been generated
    schedule_generated_through = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
