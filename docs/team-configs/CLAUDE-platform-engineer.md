# DataPulse — Platform Engineer

## Your Role

You own the platform layer that everyone else builds on: the FastAPI application factory, multi-strategy authentication (Keycloak OIDC), tenant-scoped RLS sessions, Redis caching with graceful degradation, dependency injection factories, rate limiting, Docker Compose infrastructure, CI/CD, and Nginx. When the API is down or auth breaks, it starts with you.

## Your Files

```
src/datapulse/api/
  app.py                     # App factory: CORS, security headers, global exception handler,
                             #   rate limiter, request logging, 12 router registrations
  auth.py                    # Multi-strategy auth: Bearer JWT + API Key + dev mode fallback
  jwt.py                     # Keycloak OIDC token validation + claims extraction
  deps.py                    # All DI factories: get_tenant_session, get_analytics_service,
                             #   get_pipeline_service, get_forecasting_service, etc.
  limiter.py                 # slowapi rate limiter (60/min analytics, 5/min mutations)
  routes/                    # All route files (health, analytics, pipeline, etc.)

src/datapulse/core/
  db.py                      # SQLAlchemy engine factory + session factory
  config.py                  # Core config helpers

src/datapulse/cache.py       # Redis cache_get / cache_set with graceful degradation
src/datapulse/cache_decorator.py  # @cached(ttl, prefix) decorator
src/datapulse/config.py      # Pydantic Settings (DATABASE_URL, CORS_ORIGINS, etc.)
src/datapulse/logging.py     # structlog setup (JSON in production, pretty in dev)
src/datapulse/types.py       # JsonDecimal type alias
src/datapulse/tasks/         # Celery app + async task execution
src/datapulse/embed/         # Iframe embed JWT token generation
src/datapulse/watcher/       # File watcher service (watchdog)

docker-compose.yml           # Production service definitions
docker-compose.override.yml  # Dev overrides (volume mounts, ports)
docker-compose.prod.yml      # Prod hardening (resource limits, read-only)
Dockerfile                   # API/app multi-stage build
frontend/Dockerfile          # Frontend multi-stage build
nginx/default.conf           # Reverse proxy + SSL termination
.github/workflows/           # CI/CD: lint, typecheck, test, frontend, docker-build, dbt-validate
Makefile                     # Convenience targets (test, lint, build, dbt)
scripts/prestart.sh          # Migration runner (runs before API starts)
.claude/                     # Claude Code settings + agent definitions
```

## Your Patterns

### App Factory

`create_app()` in `app.py` is the only entry point. Middleware is applied in reverse order (last added = first executed). Current stack: Security headers -> Request logging -> CORS. Rate limiter is registered separately via `app.state.limiter`.

```python
# src/datapulse/api/app.py
def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(log_format=settings.log_format)

    app = FastAPI(title="DataPulse API", version="0.1.0")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Pipeline-Token"])

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=request.url.path,
                     error=str(exc), traceback=traceback.format_exc())
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health.router)
    app.include_router(analytics.router, prefix="/api/v1")
    # ... 10 more routers
    return app
```

### Multi-Strategy Auth + Tenant Session

Auth tries: (1) Bearer JWT from Keycloak, (2) X-API-Key header, (3) dev mode when both unconfigured. The tenant session extracts `tenant_id` from JWT claims and sets it via `SET LOCAL` for PostgreSQL RLS.

```python
# src/datapulse/api/deps.py
def get_tenant_session(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> Generator[Session, None, None]:
    """DB session scoped to the authenticated user's tenant via SET LOCAL."""
    tenant_id = user.get("tenant_id", "1")
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

SessionDep = Annotated[Session, Depends(get_tenant_session)]
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
```

### DI Factory Pattern

Every service is built fresh per request via a factory function. Inject `session` (already tenant-scoped) into repositories, then compose into service.

```python
def get_analytics_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> AnalyticsService:
    repo = AnalyticsRepository(session)
    detail_repo = DetailRepository(session)
    breakdown_repo = BreakdownRepository(session)
    comparison_repo = ComparisonRepository(session)
    hierarchy_repo = HierarchyRepository(session)
    advanced_repo = AdvancedRepository(session)
    return AnalyticsService(
        repo, detail_repo, breakdown_repo, comparison_repo, hierarchy_repo, advanced_repo
    )
```

### Redis Graceful Degradation

`cache_get` / `cache_set` return `None` / silently fail if Redis is unavailable. Never let a cache miss crash an endpoint. The `@cached` decorator in `cache_decorator.py` uses MD5 of serialized params as the cache key suffix.

```python
# src/datapulse/cache.py
def cache_get(key: str) -> dict | None:
    client = _get_redis()
    if client is None:
        return None          # Redis down — app continues without cache
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None

def cache_set(key: str, value: dict, ttl: int = 300) -> None:
    client = _get_redis()
    if client is None:
        return               # Silent no-op when Redis unavailable
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass
```

### Celery Async Tasks

Long-running queries (exports, AI summaries, forecasting refresh) run as Celery tasks. Route via `tasks/` module. Tasks use the same tenant session pattern — set `app.tenant_id` before any query.

## Your Agents

- `/add-docker-service <name> <image>` — Add service to all 3 compose files with healthcheck, resource limits, restart policy, and env var documentation.
- `/coverage-check api` — Run API tests, find uncovered paths (auth branches, error handlers, middleware), suggest test additions.

## Your Commands

```bash
# Validate compose files
docker compose config --quiet

# Start all services
docker compose up -d --build

# Tail API logs
docker compose logs -f api

# Run all Python tests
make test

# Run linter
make lint

# Run auth/API tests specifically
pytest tests/test_auth.py tests/test_deps.py -v

# Type check
mypy src/datapulse/api/ --ignore-missing-imports

# Check rate limiter is working
curl -X POST http://localhost:8000/api/v1/pipeline/trigger \
  -H "X-API-Key: $API_KEY" --data '{}' --repeat 10

# Restart just the API container
docker compose restart api
```

## Your Rules

1. **`SET LOCAL` scope is per-transaction.** `get_tenant_session()` sets `app.tenant_id` inside a transaction — it never leaks across requests. Never use `SET` (session-level) instead of `SET LOCAL`.

2. **CORS origins are a JSON array string in `.env`.** `CORS_ORIGINS='["http://localhost:3000"]'` — not a comma-separated list. Validate with `docker compose config` after changes.

3. **Health endpoint returns 503 when DB is unreachable.** Never return 200 when the DB is down — upstream load balancers use health checks for routing decisions.

4. **Rate limiter must be disabled in tests.** `conftest.py` sets `limiter.enabled = False` session-scoped. New test modules that bypass `conftest.py` must do the same.

5. **Every new Docker service needs:** `healthcheck`, memory/CPU limits, `restart: unless-stopped`, named volume if stateful, and env var defaults documented in `.env.example`.

6. **Secrets via `${VAR:?must be set}` in compose.** Never hardcode secrets. If a var has no reasonable default, use the `:?` syntax to fail loudly at startup.

7. **Global exception handler returns generic 500.** Never leak stack traces, class names, or DB connection strings to clients. Log the full traceback server-side via structlog.

8. **Security headers on every response.** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or `SAMEORIGIN` for embed paths), `Referrer-Policy`. The middleware in `app.py` handles this — don't bypass it.

9. **`conftest.py` is shared infrastructure.** When you add new DI dependencies to `deps.py`, update `conftest.py` so all 80 test files can override them. Always keep `api_client` and `pipeline_api_client` fixtures working.

10. **Coverage: 95%+ in CI.** `--cov-fail-under=95` is enforced. The auth fallback chain (JWT / API Key / dev mode), error handlers, and middleware branches are common coverage gaps — test them explicitly.

---

## Project Overview

A data analytics platform for sales data: import raw Excel/CSV files, clean and transform through a medallion architecture (bronze/silver/gold), analyze with SQL, and visualize on interactive dashboards.

**Pipeline**: Import (Bronze) -> Clean (Silver) -> Analyze (Gold) -> Dashboard

## Architecture

### Medallion Data Architecture

```
Excel/CSV files
     |
     v
[Bronze Layer]  -- Raw data, as-is from source
     |              Polars + PyArrow -> Parquet -> PostgreSQL typed tables
     v
[Silver Layer]  -- Cleaned, deduplicated, type-cast
     |              dbt models (views/tables in silver schema)
     v
[Gold Layer]    -- Aggregated, business-ready metrics
                    dbt models (tables in marts schema)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Processing | Polars + PyArrow |
| Database | PostgreSQL 16 (Docker) |
| Data Transform | dbt-core + dbt-postgres |
| Config | Pydantic Settings |
| Logging | structlog |
| ORM | SQLAlchemy 2.0 |
| Containers | Docker Compose |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Data Fetching | SWR |

## Full Project Structure

```
src/datapulse/
├── config.py                    # Pydantic settings
├── bronze/                      # Raw ingestion
├── analytics/                   # Gold layer queries + service
├── pipeline/                    # Pipeline tracking + execution + quality
├── api/
│   ├── app.py                   # App factory
│   ├── auth.py                  # Multi-strategy auth
│   ├── jwt.py                   # Keycloak OIDC validation
│   ├── deps.py                  # DI factories
│   ├── limiter.py               # Rate limiter
│   └── routes/
├── core/                        # db.py, config.py
├── cache.py                     # Redis cache_get/cache_set
├── cache_decorator.py           # @cached decorator
├── tasks/                       # Celery tasks
├── embed/                       # Embed token generation
├── watcher/                     # File watcher
├── logging.py
└── types.py

dbt/
migrations/
n8n/workflows/
frontend/
  Dockerfile
  src/
android/
tests/
  conftest.py                    # Shared fixtures (all 80 test files use this)
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `redis` | datapulse-redis | (internal) | Redis cache for n8n |
| `n8n` | datapulse-n8n | 5678 | n8n workflow automation |
| `keycloak` | datapulse-keycloak | 8080 | Auth (OAuth2/OIDC) |

```bash
docker compose up -d --build
```

## Database

### Schemas (Medallion)

| Schema | Purpose | Populated by |
|--------|---------|-------------|
| `bronze` | Raw data, as-is from source | Python bronze loader |
| `public_staging` / `silver` | Cleaned, transformed | dbt staging models |
| `public_marts` / `gold` | Aggregated, business-ready | dbt marts models |

### Security Model

- Tenant-scoped RLS on all tables via `SET LOCAL app.tenant_id = '<id>'`
- `FORCE ROW LEVEL SECURITY` — owner bypass prevented
- Reader role (`datapulse_reader`) — SELECT only, scoped by tenant
- Owner role (`datapulse`) — full access (used by API)

## Configuration

All settings via environment variables or `.env` file (Pydantic Settings):

| Setting | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | `postgresql://datapulse:<password>@localhost:5432/datapulse` | PostgreSQL connection |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins (JSON list) |
| `BRONZE_BATCH_SIZE` | 50,000 | Rows per insert batch |

## Conventions

### Code Style (Python)
- Python 3.11+, Ruff for linting (line-length=100)
- Pydantic models for all config and data contracts
- structlog for structured JSON logging
- Type hints on all public functions
- Small files (200-400 lines)
- Functions < 50 lines, no nesting > 4 levels

### Security
- **Authentication**: Keycloak OIDC — JWT validation in `src/datapulse/api/jwt.py`
- Multi-strategy: Bearer JWT -> API Key -> dev mode fallback
- All credentials via `.env` (never hardcoded)
- Docker ports bound to `127.0.0.1` only
- CORS restricted to specific headers only
- Global exception handler: never leak tracebacks to clients

### Testing
- pytest + pytest-cov: 80 test files, ~1,179 test functions
- Current coverage: 95%+ (enforced in CI via `--cov-fail-under=95`)
- Playwright E2E tests: 11 spec files
- Run tests: `make test`
- `conftest.py` provides mocked repos, test client, disabled rate limiter

## Team Structure & Roles

| Role | Key Directories |
|------|----------------|
| **Pipeline Engineer** | `bronze/`, `pipeline/`, `dbt/`, `migrations/`, `n8n/` |
| **Analytics Engineer** | `analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` |
| **Platform Engineer** | `api/`, `core/`, `cache*.py`, `tasks/`, `docker-compose*.yml` |
| **Frontend Engineer** | `frontend/src/` |
| **Quality & Growth Engineer** | `tests/`, `frontend/e2e/`, `android/`, `docs/` |

## Architecture Documentation

See `docs/ARCHITECTURE.md` for system diagrams, data flow, ERD, and deployment architecture.
