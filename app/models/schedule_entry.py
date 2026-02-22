"""ScheduleEntry model — a single programme slot in a channel's schedule."""

from sqlalchemy import Column, Integer, String, DateTime, Text, Index, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class ScheduleEntry(Base):
    """
    A single programme entry in a channel's schedule.

    start_time and end_time are stored in UTC. The end_time is always
    start_time + duration, stored redundantly for efficient range queries.

    The composite index on (channel_id, start_time) enables fast lookups
    for "what is playing now" and EPG guide generation.
    """

    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False
    )

    # Programme metadata
    title = Column(String(255), nullable=False)
    series_name = Column(String(255), nullable=True)
    season_number = Column(Integer, nullable=True)
    episode_number = Column(Integer, nullable=True)

    # Jellyfin references
    media_item_id = Column(String(255), nullable=False)  # Jellyfin item ID
    library_id = Column(String(255), nullable=False)

    # Classification
    item_type = Column(String(50), nullable=False)       # "Movie" | "Episode"
    genres = Column(Text, nullable=True)                 # JSON array e.g. '["Sci-Fi"]'

    # Timing (UTC)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)          # start_time + duration
    duration = Column(Integer, nullable=False)           # seconds

    # Local file path for direct streaming (faster seek than HTTP).
    # Populated at schedule generation time from Jellyfin's Path field.
    # May be None for older entries or when running on a different machine
    # without a MEDIA_PATH_MAP configured.
    file_path = Column(Text, nullable=True)

    # Sidecar metadata — read from the .nfo / .jpg files next to the video.
    description    = Column(Text, nullable=True)         # <plot> from .nfo
    content_rating = Column(String(20), nullable=True)   # <mpaa> e.g. "TV-14"
    thumbnail_path = Column(Text, nullable=True)         # absolute path to .jpg
    air_date       = Column(String(20), nullable=True)   # "YYYY-MM-DD" from <aired>

    created_at = Column(DateTime, server_default=func.now())

    # Compound index for fast EPG and "now playing" queries
    __table_args__ = (
        Index("ix_schedule_channel_time", "channel_id", "start_time"),
    )
