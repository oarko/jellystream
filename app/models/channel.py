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

    # ── Transcode settings (per-channel ffmpeg tuning) ─────────────────────────
    # Max output height in pixels; source is scaled down to fit (aspect kept).
    # NULL or 0 = no downscale — pass the source's native resolution through.
    transcode_max_height = Column(Integer, nullable=True, default=1080)

    # libx264/QSV named preset controlling encode speed vs quality. Ignored
    # by the "vaapi" hwaccel path (VAAPI has no equivalent preset concept).
    # One of: ultrafast, superfast, veryfast, faster, fast, medium.
    transcode_preset = Column(String(20), nullable=False, default="veryfast")

    # Hardware-accelerated decode/encode backend.
    # "none" (software libx264, default) | "vaapi" (Intel/AMD) | "qsv" (Intel
    # Quick Sync) | "nvenc" (NVIDIA).
    hwaccel = Column(String(20), nullable=False, default="none")

    # Optional device path for the hwaccel backend, e.g. "/dev/dri/renderD128"
    # for vaapi when a machine has more than one GPU. Blank = auto-detect.
    hwaccel_device = Column(String(255), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
