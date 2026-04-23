"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings

logger = structlog.get_logger()

_DEV_ENVS = frozenset({"development", "test"})


def is_non_dev_env(app_env: str, sentry_environment: str) -> bool:
    """Return True when either env label signals a non-development deployment.

    Defense in depth for security-sensitive gates (auth fallback, secret
    requirements). A single misconfigured variable must not open the gate —
    see issue #537.
    """
    return app_env not in _DEV_ENVS or sentry_environment not in _DEV_ENVS


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

    # Auth provider discriminator — the single source of truth for which
    # IdP verifies Bearer JWTs. Default is "auth0" so existing deployments
    # keep their behavior; set AUTH_PROVIDER=clerk in .env to swap providers.
    # Both provider configs coexist so switching back is a one-line env change.
    auth_provider: Literal["auth0", "clerk"] = "auth0"

    # Auth0 OIDC
    auth0_domain: str = ""  # e.g. "datapulse.us.auth0.com"
    auth0_client_id: str = ""  # Application Client ID
    auth0_client_secret: str = ""  # Application Client Secret
    auth0_audience: str = ""  # API identifier, e.g. "https://api.datapulse.tech"

    # Clerk — temporary replacement for Auth0 while clients are small.
    # All CLERK_* fields are empty when AUTH_PROVIDER=auth0.
    clerk_publishable_key: str = ""  # pk_test_... or pk_live_...
    clerk_secret_key: str = ""  # sk_test_... or sk_live_... (backend admin ops)
    clerk_frontend_api: str = ""  # e.g. "https://<slug>.clerk.accounts.dev"
    clerk_jwt_issuer: str = ""  # JWT `iss` claim — usually == clerk_frontend_api
    clerk_jwt_audience: str = ""  # Optional; empty == skip `aud` verification
    clerk_jwt_template: str = "datapulse"  # Name of the JWT template (claim shape)

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

    # Deployment mode — authoritative flag for security-sensitive gates.
    # One of: "development", "test", "staging", "production".
    # SECURITY: this is the only field that should gate auth/security
    # behavior. Keep distinct from sentry_environment (telemetry label)
    # so the two cannot be conflated (see issue #537).
    app_env: str = "development"

    # Sentry (error tracking) — telemetry label, NOT a security boundary.
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1  # 10% performance monitoring

    # Lead capture — optional webhook for HubSpot / Pipedrive / Zapier CRM sync.
    # Leave empty to disable. Set LEAD_NOTIFY_URL=https://hooks.zapier.com/... to enable.
    lead_notify_url: str = ""

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

    # Paymob (EGP) — Egypt PMF #604
    paymob_api_key: str = ""
    paymob_integration_id: str = ""  # online card integration ID from dashboard
    paymob_iframe_id: str = ""  # iframe ID from Paymob dashboard
    paymob_hmac_secret: str = ""  # HMAC secret for webhook verification

    # Control Center — credential encryption key (pgcrypto pgp_sym_encrypt)
    # Generate with: openssl rand -base64 48
    # Must be set when using Postgres/SQL Server connectors with stored passwords.
    control_center_creds_key: str = ""

    @model_validator(mode="after")
    def _reject_cors_wildcard_with_credentials(self) -> "Settings":
        """Reject ``CORS_ORIGINS=['*']`` because the CORS middleware always
        runs with ``allow_credentials=True`` (see
        ``datapulse.api.bootstrap.middleware``). The browser rejects that
        combination and any proxy that honors it is a CSRF-grade hole
        (#546). Operators who genuinely want an open API must list origins
        explicitly.
        """
        if "*" in self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS=['*'] is forbidden because credentials are "
                "allowed — list origins explicitly (e.g. "
                "'https://app.example.com,https://admin.example.com')."
            )
        return self

    @model_validator(mode="after")
    def _require_auth_in_production(self) -> "Settings":
        """Fail fast at startup if auth is unconfigured in non-dev environments.

        Defense in depth: refuse to boot when *either* ``app_env`` or
        ``sentry_environment`` signals a non-dev deployment. Using OR instead
        of AND means a single misconfigured variable cannot bypass the gate
        (see issue #537).
        """
        if (
            is_non_dev_env(self.app_env, self.sentry_environment)
            and not self.api_key
            and not self._jwt_provider_configured
        ):
            raise ValueError(
                "Auth must be configured in production/staging "
                f"(app_env={self.app_env!r}, "
                f"sentry_environment={self.sentry_environment!r}, "
                f"auth_provider={self.auth_provider!r}). "
                "Set API_KEY, or AUTH0_DOMAIN (auth_provider=auth0), "
                "or CLERK_SECRET_KEY+CLERK_JWT_ISSUER (auth_provider=clerk)."
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
        """Fail fast in non-dev environments when critical secrets are missing.

        Like ``_require_auth_in_production``, this validator trips whenever
        *either* ``app_env`` or ``sentry_environment`` indicates a non-dev
        deployment — so a misconfigured single variable cannot bypass it.
        """
        if not is_non_dev_env(self.app_env, self.sentry_environment):
            return self

        missing: list[str] = []
        if not self.api_key and not self._jwt_provider_configured:
            if self.auth_provider == "clerk":
                missing.append("API_KEY or CLERK_SECRET_KEY+CLERK_JWT_ISSUER")
            else:
                missing.append("API_KEY or AUTH0_DOMAIN")
        if not self.db_reader_password:
            missing.append("DB_READER_PASSWORD")
        if not self.pipeline_webhook_secret:
            missing.append("PIPELINE_WEBHOOK_SECRET")

        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(
                f"Missing required secrets for {self.sentry_environment}: {missing_list}"
            )

        return self

    @model_validator(mode="after")
    def _warn_on_auth_provider_mismatch(self) -> "Settings":
        """Catch the common foot-gun where only half of a provider swap lands.

        If the operator fills CLERK_* secrets but leaves AUTH_PROVIDER=auth0
        (or vice-versa), the backend happily reads the wrong JWKS/issuer and
        every valid token 401s. We can't *correct* it (intent is ambiguous)
        but we can log loudly so it shows up in the first startup line.
        """
        if self.auth_provider == "auth0" and self.clerk_secret_key:
            logger.warning(
                "auth_provider_mismatch",
                detail="CLERK_SECRET_KEY is set but AUTH_PROVIDER=auth0 — "
                "Clerk config is ignored. Set AUTH_PROVIDER=clerk to activate.",
            )
        if self.auth_provider == "clerk" and self.auth0_domain:
            logger.warning(
                "auth_provider_mismatch",
                detail="AUTH0_DOMAIN is set but AUTH_PROVIDER=clerk — "
                "Auth0 config is ignored. Set AUTH_PROVIDER=auth0 to revert.",
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

    @property
    def clerk_jwks_url(self) -> str:
        """Clerk JWKS endpoint — derived from ``clerk_frontend_api`` when set,
        otherwise empty so the active-* selector can signal misconfiguration.
        """
        if not self.clerk_frontend_api:
            return ""
        return f"{self.clerk_frontend_api.rstrip('/')}/.well-known/jwks.json"

    @property
    def _jwt_provider_configured(self) -> bool:
        """Whether the selected IdP has enough config to verify tokens."""
        if self.auth_provider == "clerk":
            return bool(self.clerk_jwt_issuer and self.clerk_frontend_api)
        return bool(self.auth0_domain)

    @property
    def active_jwks_url(self) -> str:
        """JWKS endpoint for the currently active IdP.

        This is the *only* JWKS URL that ``core/jwt.py`` should read. Swapping
        providers is a matter of flipping ``AUTH_PROVIDER`` in .env — neither
        verification code nor call sites need to branch.
        """
        return self.clerk_jwks_url if self.auth_provider == "clerk" else self.auth0_jwks_url

    @property
    def active_issuer_url(self) -> str:
        """Expected ``iss`` claim for the currently active IdP."""
        return self.clerk_jwt_issuer if self.auth_provider == "clerk" else self.auth0_issuer_url

    @property
    def active_audience(self) -> str:
        """Expected ``aud`` claim — empty string means skip ``aud`` verification.

        Clerk's default JWT templates do not set ``aud``; only set
        ``CLERK_JWT_AUDIENCE`` if you configured an audience on the template.
        """
        return self.clerk_jwt_audience if self.auth_provider == "clerk" else self.auth0_audience

    @property
    def active_expected_azp(self) -> str:
        """Expected ``azp`` (authorized party) claim — empty means skip check.

        Auth0 puts the application client_id in ``azp``. Clerk puts its
        Frontend API URL there; we deliberately skip that check because the
        issuer check already verifies the token came from our Clerk instance.
        """
        return self.auth0_client_id if self.auth_provider == "auth0" else ""

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
        if not self._jwt_provider_configured:
            missing = (
                "CLERK_JWT_ISSUER+CLERK_FRONTEND_API"
                if self.auth_provider == "clerk"
                else "AUTH0_DOMAIN"
            )
            logger.warning(
                "auth_disabled",
                provider=self.auth_provider,
                detail=f"{missing} is empty — JWT authentication is disabled",
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
