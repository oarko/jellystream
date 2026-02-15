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
    JELLYFIN_CLIENT_NAME: str = "JellyStream"
    JELLYFIN_DEVICE_NAME: str = "JellyStream Server"
    JELLYFIN_DEVICE_ID: str = ""  # Auto-generated if not provided

    # Paths
    COMMERCIALS_PATH: str = "./data/commercials"
    LOGOS_PATH: str = "./data/logos"

    # Scheduler
    SCHEDULER_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
