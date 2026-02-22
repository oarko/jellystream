"""Pydantic request/response schemas for JellyStream API."""

from typing import List, Optional
from pydantic import BaseModel


# ─── Channel Schemas ──────────────────────────────────────────────────────────

class LibraryConfig(BaseModel):
    """A Jellyfin library attached to a channel."""
    library_id: str
    library_name: str
    collection_type: str  # "movies" | "tvshows" | "mixed"


class GenreFilterConfig(BaseModel):
    """A genre filter applied to a channel's schedule generation."""
    genre: str
    content_type: str = "both"   # "movie" | "episode" | "both"
    filter_type: str = "include"  # "include" | "exclude"


class CreateChannelRequest(BaseModel):
    """Request body for POST /api/channels/"""
    name: str
    description: Optional[str] = None
    channel_number: Optional[str] = None
    channel_type: str = "video"        # "video" | "music" (music planned)
    schedule_type: str = "genre_auto"  # "manual" | "genre_auto"
    libraries: List[LibraryConfig]
    genre_filters: Optional[List[GenreFilterConfig]] = None


class UpdateChannelRequest(BaseModel):
    """Request body for PUT /api/channels/{id}"""
    name: Optional[str] = None
    description: Optional[str] = None
    channel_number: Optional[str] = None
    enabled: Optional[bool] = None
    channel_type: Optional[str] = None
    schedule_type: Optional[str] = None
    libraries: Optional[List[LibraryConfig]] = None
    genre_filters: Optional[List[GenreFilterConfig]] = None


# ─── Schedule Schemas ─────────────────────────────────────────────────────────

class CreateScheduleEntryRequest(BaseModel):
    """Request body for POST /api/schedules/"""
    channel_id: int
    title: str
    media_item_id: str
    library_id: str
    item_type: str          # "Movie" | "Episode"
    start_time: str         # ISO 8601 datetime string
    duration: int           # seconds
    series_name: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    genres: Optional[str] = None  # JSON array string e.g. '["Sci-Fi","Action"]'


class UpdateScheduleEntryRequest(BaseModel):
    """Request body for PUT /api/schedules/{id}"""
    title: Optional[str] = None
    media_item_id: Optional[str] = None
    start_time: Optional[str] = None   # ISO 8601
    duration: Optional[int] = None
    series_name: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None


# ─── Live TV Registration Schemas ─────────────────────────────────────────────

class RegisterLiveTVRequest(BaseModel):
    """
    Request body for POST /api/channels/{id}/register-livetv

    public_url must be reachable from the Jellyfin server
    (e.g. "http://192.168.1.100:8000").
    """
    public_url: str                        # JellyStream base URL as seen by Jellyfin
    tuner_count: int = 1                   # Max simultaneous streams (0 = unlimited)
    allow_hw_transcoding: bool = False
    allow_fmp4_transcoding: bool = False
    allow_stream_sharing: bool = True
    enable_stream_looping: bool = True
    fallback_max_bitrate: int = 0          # 0 = no limit
    ignore_dts: bool = False
    read_at_native_framerate: bool = False
