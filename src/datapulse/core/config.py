"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

import structlog
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logger = structlog.get_logger()


class ForecastConfig(BaseModel):
    """Forecasting hyperparameters — extracted from hardcoded values."""

    daily_seasonality: int = 7
    monthly_seasonality: int = 12
    daily_horizon: int = 30
    monthly_horizon: int = 3
    product_horizon: int = 3
    top_products: int = 50
    daily_lookback_days: int = 730
    default_confidence: float = 0.80
    trend_threshold: float = 0.05
    min_clamp: float = 0.01
    sma_window: int = 30


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
    cors_origins: list[str] = []  # Empty = block all CORS; set CORS_ORIGINS in .env for dev

    # Pipeline execution
    dbt_project_dir: str = "/app/dbt"
    dbt_profiles_dir: str = "/app/dbt"
    raw_sales_path: str = "/app/data/raw/sales"
    pipeline_bronze_timeout: int = 600  # seconds
    pipeline_dbt_timeout: int = 300  # seconds

    # API base URL (used by watcher and internal services)
    api_base_url: str = "http://localhost:8000"

    # n8n removed — orchestration via datapulse.scheduler
    pipeline_webhook_secret: str = ""

    # API security
    api_key: str = ""
    api_key_roles: list[str] = ["api-reader"]
    default_tenant_id: str = "1"

    # RBAC — emails that auto-register with elevated roles on first login
    owner_emails: list[str] = ["admin@rahmaqanater.org"]
    admin_emails: list[str] = ["dr.engy@saas.com"]

    # Embed token signing
    embed_secret: str = ""

    # Auth0 OIDC (replaces Keycloak — see Wild Wolf beta release plan)
    auth0_domain: str = ""  # e.g. "datapulse.us.auth0.com"
    auth0_client_id: str = ""  # Application Client ID
    auth0_client_secret: str = ""  # Application Client Secret
    auth0_audience: str = ""  # API identifier, e.g. "https://api.datapulse.tech"

    # Redis cache
    redis_url: str = ""
    redis_default_ttl: int = 300  # 5 minutes
    redis_dashboard_ttl: int = 600  # 10 minutes

    # Async query execution (Redis db 2 for job state)
    query_row_limit: int = 10_000  # Max rows for async queries

    # Embed (iframe white-label)
    embed_allowed_origins: list[str] = []  # Domains allowed to iframe embed

    # Sentry (error tracking)
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1  # 10% performance monitoring

    # Logging
    log_format: str = "console"

    # OpenRouter (AI-Light)
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"

    # Forecasting
    forecast: ForecastConfig = ForecastConfig()

    # Notifications
    slack_webhook_url: str = ""
    notification_email: str = ""

    # Stripe billing
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""  # price_xxx from Stripe Dashboard
    billing_base_url: str = "https://smartdatapulse.tech"

    @property
    def stripe_price_to_plan_map(self) -> dict[str, str]:
        """Map Stripe Price IDs to internal plan names."""
        mapping: dict[str, str] = {}
        if self.stripe_price_pro_monthly:
            mapping[self.stripe_price_pro_monthly] = "pro"
        return mapping

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def auth0_issuer_url(self) -> str:
        """Auth0 issuer URL — matches the ``iss`` claim in tokens."""
        return f"https://{self.auth0_domain}/"

    @property
    def auth0_jwks_url(self) -> str:
        """Auth0 JWKS endpoint for JWT signature verification."""
        return f"https://{self.auth0_domain}/.well-known/jwks.json"

    def warn_if_auth_disabled(self) -> None:
        """Log warnings when authentication secrets are not configured."""
        env = self.sentry_environment

        if not self.api_key:
            logger.warning(
                "auth_disabled",
                detail="API_KEY is empty — API key authentication is disabled",
            )
        if not self.pipeline_webhook_secret:
            logger.warning(
                "auth_disabled",
                detail="PIPELINE_WEBHOOK_SECRET is empty — pipeline token auth is disabled",
            )
        if not self.auth0_domain:
            logger.warning(
                "auth_disabled",
                detail="AUTH0_DOMAIN is empty — JWT authentication is disabled",
            )

        # Warn about localhost CORS in non-dev environments
        if env not in ("development", "test"):
            localhost_origins = [o for o in self.cors_origins if "localhost" in o]
            if localhost_origins:
                logger.warning(
                    "cors_localhost_in_production",
                    origins=localhost_origins,
                    detail="CORS allows localhost origins in non-dev environment",
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    settings = Settings()  # type: ignore[call-arg]
    settings.warn_if_auth_disabled()
    return settings
