"""Configuration for Hungarian Tarokk server."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Server configuration settings."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Logging
    log_level: str = "INFO"

    # Statistics: /stats answers only to this token; without one it does not exist
    stats_token: Optional[str] = None

    # CORS
    cors_origins: str = "*"  # Comma-separated list or "*"

    # Game
    max_rooms: int = 100  # Tables open at the same time; a new one is refused beyond this
    closed_room_keep_days: int = 7  # How long a closed table stays in the database

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
