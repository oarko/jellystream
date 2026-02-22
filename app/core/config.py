"""Application configuration."""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "JellyStream"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = "sqlite:///./data/database/jellystream.db"

    # Jellyfin
    JELLYFIN_URL: str = ""
    JELLYFIN_API_KEY: str = ""
    JELLYFIN_USER_ID: str = ""  # User ID for API requests (can be auto-detected)
    JELLYFIN_CLIENT_NAME: str = "JellyStream"
    JELLYFIN_DEVICE_NAME: str = "JellyStream Server"
    JELLYFIN_DEVICE_ID: str = ""  # Auto-generated if not provided
    JELLYFIN_DEFAULT_PAGE_SIZE: int = 50  # Default items per page
    JELLYFIN_MAX_PAGE_SIZE: int = 1000  # Maximum items per page

    # JellyStream network
    # The base URL Jellyfin (and other clients) use to reach THIS JellyStream
    # instance — must be a network-accessible IP, NOT localhost.
    # Example: http://192.168.1.100:8000
    JELLYSTREAM_PUBLIC_URL: str = ""

    # Stream proxy
    # ISO 639-2 language code for preferred audio track selection.
    # Examples: eng (English), fre (French), spa (Spanish), jpn (Japanese)
    # JellyStream will use ffprobe to find a matching track; falls back to the
    # first audio track if the preferred language is not present.
    PREFERRED_AUDIO_LANGUAGE: str = "eng"

    # Media path mapping for direct file access.
    # Maps the path prefix Jellyfin reports to the path where the same
    # files are accessible on THIS machine.
    # Format: "/jellyfin/prefix:/local/prefix"
    # Example: "/media:/mnt/nas/media" or leave blank if same machine.
    MEDIA_PATH_MAP: str = ""

    # Paths
    COMMERCIALS_PATH: str = "./data/commercials"
    LOGOS_PATH: str = "./data/logos"

    # Scheduler
    SCHEDULER_ENABLED: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_TO_FILE: bool = True
    LOG_FILE_PATH: str = "./logs"
    LOG_FILE_MAX_BYTES: int = 10485760  # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_RETENTION_DAYS: int = 30  # Delete logs older than this

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
