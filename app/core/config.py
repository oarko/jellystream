"""Application configuration."""

from typing import Any, List
from pydantic import model_validator
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
    LOG_TO_CONSOLE: bool = True  # set False under systemd to avoid duplicating
    # the same lines into both ./logs/jellystream_*.log and the journal
    LOG_TO_FILE: bool = True
    LOG_FILE_PATH: str = "./logs"
    LOG_FILE_MAX_BYTES: int = 10485760  # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_RETENTION_DAYS: int = 30  # Delete logs older than this

    class Config:
        env_file = ".env"
        case_sensitive = True

    @model_validator(mode="before")
    @classmethod
    def _blank_env_vars_use_defaults(cls, data: Any) -> Any:
        """
        Treat an empty string from .env — or a value that's nothing but a
        stray inline comment — as "not set" rather than a literal value, so
        the field's coded default applies instead of a hard crash at
        startup (e.g. LOG_RETENTION_DAYS= with nothing after the "=" fails
        int parsing otherwise).

        The "#comment" case handles a specific, previously-observed
        corruption: .env.example has lines like
        "JELLYFIN_USER_ID=  # Optional, auto-detected if left empty" —
        relying on dotenv's rule that only an unquoted value followed by
        whitespace-then-# is a stripped inline comment. If anything
        re-serializes that file and trims the leading whitespace before the
        "#" (as the setup wizard's config round-trip did), the value becomes
        the literal string "# Optional, auto-detected if left empty" — a
        non-empty, seemingly valid string that silently defeats
        auto-detection instead of erroring. No field in this app has a
        legitimate value starting with "#", so treat that the same as blank.

        A blank/comment-only .env line is a config-editing slip either way,
        not an intentional value — no field here needs "" or a bare comment
        to mean something different from being absent; the string fields
        that DO default to "" (JELLYFIN_USER_ID, MEDIA_PATH_MAP, etc.) end
        up at that same default regardless.
        """
        if not isinstance(data, dict):
            return data

        def is_blank(v: Any) -> bool:
            if not isinstance(v, str):
                return False
            v = v.strip()
            return v == "" or v.startswith("#")

        return {k: v for k, v in data.items() if not is_blank(v)}


settings = Settings()
