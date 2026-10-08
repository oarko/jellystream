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

    # ── On-screen graphic ("bug") ───────────────────────────────────────────────
    # Absolute path to the uploaded image (under LOGOS_PATH), or NULL if none
    # has been uploaded. The bug never appears unless BOTH this is set AND
    # bug_enabled is true.
    bug_image_path = Column(String(500), nullable=True)
    bug_enabled = Column(Boolean, nullable=False, default=False)

    # "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center"
    bug_position = Column(String(20), nullable=False, default="bottom-right")

    # How often the bug appears, in seconds. 0 = always visible while
    # bug_enabled (no flashing). >0 = appears for bug_duration_seconds every
    # bug_interval_seconds, restarting from the beginning of each schedule
    # entry (each is a separate ffmpeg process).
    bug_interval_seconds = Column(Integer, nullable=False, default=0)
    bug_duration_seconds = Column(Integer, nullable=False, default=10)

    # The bug's width as a percentage of the video's width; height follows
    # automatically from the image's own aspect ratio (unless capped below).
    bug_scale_percent = Column(Integer, nullable=False, default=12)

    # Upper bound on the bug's height, as a percentage of the video's height —
    # independent of bug_scale_percent, so a tall/narrow image can't blow up
    # to an unreasonable height just because its width fits the width cap.
    # Whichever of the two constraints (width % or height %) is more
    # restrictive wins; aspect ratio is always preserved.
    bug_max_height_percent = Column(Integer, nullable=False, default=30)

    # The bug's opacity, 1-100 (100 = fully opaque, as the source image's own
    # alpha channel — if any — already defines it). Below 100, this is
    # multiplied into whatever alpha the image already has, so a PNG with
    # partial transparency still gets proportionally more transparent rather
    # than having its own alpha overridden.
    bug_opacity_percent = Column(Integer, nullable=False, default=100)

    # ── Channel logo (shown in the Jellyfin/IPTV guide, not on the video) ──────
    # Absolute path to a dedicated logo image under LOGOS_PATH, or NULL.
    # Ignored when logo_use_bug_image is true (see below).
    logo_image_path = Column(String(500), nullable=True)

    # When true, the channel logo IS the on-screen graphic image
    # (bug_image_path) — one upload serves both purposes instead of two.
    # logo_image_path is left on disk untouched while this is true, so
    # turning it back off restores whatever dedicated logo was there before.
    logo_use_bug_image = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
