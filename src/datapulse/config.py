"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """DataPulse configuration — reads from .env file."""

    # Database
    database_url: str = "postgresql://datapulse:CHANGEME@localhost:5432/datapulse"

    # Paths
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    parquet_dir: Path = Path("data/processed/parquet")

    # Limits
    max_file_size_mb: int = 500
    max_rows: int = 10_000_000
    max_columns: int = 200

    # Bronze loader
    bronze_batch_size: int = 50_000

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
