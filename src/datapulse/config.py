"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """DataPulse configuration — reads from .env file."""

    # Database — no default; MUST be set via env / .env
    database_url: str

    # Database connection pool
    db_pool_size: int = 10
    db_pool_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

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

    # Pipeline execution
    dbt_project_dir: str = "/app/dbt"
    dbt_profiles_dir: str = "/app/dbt"
    raw_sales_path: str = "/app/data/raw/sales"
    pipeline_bronze_timeout: int = 600   # seconds
    pipeline_dbt_timeout: int = 300      # seconds

    # n8n
    n8n_webhook_url: str = "http://n8n:5678/webhook/"
    pipeline_webhook_secret: str = ""

    # API security
    api_key: str = ""

    # Logging
    log_format: str = "console"

    # OpenRouter (AI-Light)
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"

    # Notifications
    slack_webhook_url: str = ""
    notification_email: str = ""

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
