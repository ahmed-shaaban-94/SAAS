"""Application settings loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """DataPulse configuration — reads from .env file."""

    # Database
    database_url: str = "postgresql://datapulse:datapulse_dev@localhost:5432/datapulse"

    # Paths
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")

    # Limits
    max_file_size_mb: int = 50
    max_rows: int = 100_000
    max_columns: int = 100

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
