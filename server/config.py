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

    # CORS
    cors_origins: str = "*"  # Comma-separated list or "*"

    # Game
    max_rooms: int = 100
    room_timeout_minutes: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
