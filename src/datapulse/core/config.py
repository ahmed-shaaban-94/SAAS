"""Application settings loaded from environment variables."""

import os
from functools import lru_cache
from pathlib import Path

import structlog
from pydantic import BaseModel, model_validator
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

    # Database connection pool — sized for multi-worker deployment.
    # With 4 prod workers: 4 x (5 + 10) = 60 max connections, fitting
    # within PostgreSQL max_connections=100 with headroom for admin/migrations.
    db_pool_size: int = 5
    db_pool_max_overflow: int = 10
    db_pool_timeout: int = 15
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

    # Watcher health endpoint. 0 disables the embedded HTTP server
    # (default — backwards compatible). Set to e.g. 8765 in Docker
    # so a container healthcheck can `curl http://localhost:8765/health`.
    watcher_health_port: int = 0
    watcher_health_host: str = "127.0.0.1"

    # n8n removed — orchestration via datapulse.scheduler
    pipeline_webhook_secret: str = ""

    # API security
    api_key: str = ""
    db_reader_password: str = ""
    api_key_roles: list[str] = ["api-reader"]
    default_tenant_id: str = "1"

    # API overload protection
    # Per-worker in-flight request cap. A small acquisition timeout lets the
    # API shed excess load quickly instead of letting workers spiral into
    # timeouts and OOMs under bursts.
    api_max_in_flight_requests: int = 64
    api_backpressure_timeout_ms: int = 75

    # RBAC — emails that auto-register with elevated roles on first login
    # Set via OWNER_EMAILS / ADMIN_EMAILS env vars (comma-separated). Empty = no auto-elevation.
    owner_emails: list[str] = []
    admin_emails: list[str] = []

    # Embed token signing
    embed_secret: str = ""

    # Auth0 OIDC
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
    query_max_concurrent_jobs: int = 4
    query_max_concurrent_jobs_per_tenant: int = 2

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

    # AI-Light — LangGraph feature flag and runtime controls
    # Set AI_LIGHT_USE_LANGGRAPH=true to enable; OFF by default.
    ai_light_use_langgraph: bool = False
    # Global daily token cap across all tenants.
    ai_light_max_tokens_per_day: int = 100_000
    # "memory" (Phase A-C) or "postgres" (Phase D HITL).
    ai_light_checkpoint_backend: str = "memory"
    # Tool-capable model, e.g. "openai/gpt-4o-mini" or "anthropic/claude-3.5-haiku".
    openrouter_agent_model: str = ""
    langsmith_api_key: str = ""  # Optional LangSmith observability
    langsmith_project: str = ""  # LangSmith project name

    # Brain (session memory) — embedding model for semantic search
    brain_embed_model: str = "openai/text-embedding-3-small"

    # Infrastructure tuning (extracted from hardcoded values)
    redis_socket_timeout: int = 2
    redis_retry_interval: int = 15
    jwks_cache_ttl: int = 3600
    query_job_ttl: int = 3600
    query_execution_timeout: int = 300
    sse_poll_interval: int = 2
    sse_max_duration: int = 600

    # Forecasting
    forecast: ForecastConfig = ForecastConfig()

    # Notifications
    slack_webhook_url: str = ""
    notification_email: str = ""

    # Control Center (data control plane) — off by default until Phase 1d lands
    feature_control_center: bool = False

    # Pharmaceutical Platform — inventory, expiry, dispensing, POS features
    feature_platform: bool = False

    # Stripe billing
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""  # price_xxx from Stripe Dashboard
    billing_base_url: str = "https://smartdatapulse.tech"

    # Control Center — credential encryption key (pgcrypto pgp_sym_encrypt)
    # Generate with: openssl rand -base64 48
    # Must be set when using Postgres/SQL Server connectors with stored passwords.
    control_center_creds_key: str = ""

    @model_validator(mode="after")
    def _require_auth_in_production(self) -> "Settings":
        """Fail fast at startup if auth is unconfigured in non-dev environments."""
        env = self.sentry_environment
        if env not in ("development", "test") and not self.api_key and not self.auth0_domain:
            raise ValueError(
                f"Auth must be configured in production/staging (environment={env!r}). "
                "Set API_KEY or AUTH0_DOMAIN in the environment."
            )
        return self

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

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        """Fail fast in non-dev environments when critical secrets are missing."""
        if self.sentry_environment in ("development", "test"):
            return self

        missing: list[str] = []
        if not self.api_key and not self.auth0_domain:
            missing.append("API_KEY or AUTH0_DOMAIN")
        if not self.db_reader_password:
            missing.append("DB_READER_PASSWORD")
        if (
            not self.pipeline_webhook_secret
            and os.getenv("PIPELINE_AUTH_DISABLED", "").lower() != "true"
        ):
            missing.append("PIPELINE_WEBHOOK_SECRET")

        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(
                f"Missing required secrets for {self.sentry_environment}: {missing_list}"
            )

        return self

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
