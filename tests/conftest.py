"""Session-scoped test configuration for DataPulse.

Problem: The project's .env file contains extra keys (POSTGRES_USER,
POSTGRES_PASSWORD, POSTGRES_DB) that
pydantic-settings rejects as "extra_forbidden" when Settings() is called.

Solution: Patch get_settings() at the session level so every call to
get_settings() in production code returns a clean Settings instance built
from defaults only (no .env file). Tests that need a custom Settings object
patch get_settings() locally within the test.
"""

import os
from unittest.mock import MagicMock, create_autospec, patch

import pytest


def pytest_configure(config):
    """Set minimal env vars and cache create_app for fast test startup.

    This runs before test collection, fixing collection errors in modules
    that call get_settings() at module level.

    Also caches create_app() so Pydantic schema generation (~10-15s) only
    happens once instead of 30+ times across test files. Without this,
    unit tests exceed the 10-minute CI timeout.
    """
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

    # Cache create_app() — replaces the module attribute before any test file
    # imports it, so both `from datapulse.api.app import create_app` and
    # `datapulse.api.app.create_app()` resolve to the cached version.
    #
    # Without this, 30+ test files each call create_app(), triggering
    # Pydantic schema generation (~10-15s each) and exceeding the
    # 10-minute CI timeout.
    #
    # The lifespan is replaced with a no-op because session fixtures
    # (_disable_scheduler) aren't active yet during the first call.
    import datapulse.api.app as _app_module

    _original = _app_module.create_app
    _cached_app = None

    def _cached_create_app():
        nonlocal _cached_app
        if _cached_app is None:
            _cached_app = _original()
            # Replace lifespan with no-op to avoid scheduler/event-loop
            # conflicts in TestClient. Session fixtures patch the scheduler
            # too late for the first cached call.
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def _noop_lifespan(app):
                yield

            _cached_app.router.lifespan_context = _noop_lifespan
        # Clear stale overrides from previous test
        _cached_app.dependency_overrides.clear()

        # Default RBAC overrides — some routes use require_permission/
        # get_access_context which calls get_session_factory() directly
        # (bypassing the mocked tenant session), hanging on DB connect.
        # Provide a default admin context; tests that need specific RBAC
        # behavior can override these.
        from datapulse.rbac.dependencies import get_access_context
        from datapulse.rbac.models import AccessContext

        _cached_app.dependency_overrides[get_access_context] = lambda: AccessContext(
            member_id=1,
            tenant_id=1,
            user_id="test-user",
            role_key="owner",
            permissions={
                "analytics:read",
                "analytics:custom_query",
                "analytics:export",
                "pipeline:read",
                "pipeline:run",
                "pipeline:trigger",
                "admin:read",
                "admin:write",
                "insights:view",
                "members:view",
                "members:manage",
                "reports:view",
                "reports:create",
                "sectors:manage",
            },
            sector_ids=[],
            is_admin=True,
        )
        return _cached_app

    _app_module.create_app = _cached_create_app


from datapulse.api.limiter import limiter  # noqa: E402
from datapulse.config import Settings, get_settings  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _disable_rate_limiting():
    """Disable rate limiting for all tests."""
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(autouse=True, scope="session")
def _disable_scheduler():
    """Prevent APScheduler from starting during tests.

    The AsyncIOScheduler can deadlock with TestClient's event loop,
    causing tests to hang indefinitely in CI.
    """
    with patch("datapulse.scheduler.scheduler") as mock_sched:
        mock_sched.running = False
        mock_sched.start = MagicMock()
        mock_sched.shutdown = MagicMock()
        mock_sched.add_job = MagicMock()
        yield


@pytest.fixture(autouse=True, scope="session")
def _disable_redis_cache():
    """Disable Redis caching so service tests hit the real (mocked) functions.

    The cache module itself is tested in test_cache.py using local mocks,
    so this global disable doesn't affect those tests — they mock
    get_redis_client() directly.
    """
    with (
        patch("datapulse.cache_decorator.cache_get", return_value=None),
        patch("datapulse.cache_decorator.cache_set"),
        patch("datapulse.cache.get_redis_client", return_value=None),
    ):
        yield


@pytest.fixture(autouse=True, scope="session")
def _patch_get_settings_globally():
    """Replace get_settings() with a version that never reads the .env file.

    This is session-scoped so it runs once and covers all tests, including
    the pre-existing tests in test_reader.py that call read_file() which
    internally calls get_settings().

    Individual tests that need custom settings values patch get_settings()
    locally — those local patches take precedence over this session patch.
    """
    # Build a clean Settings instance without touching the project's .env
    clean_settings = Settings(_env_file=None, api_key="test-api-key", database_url="")
    get_settings.cache_clear()

    # Patch the imported references in each module that uses get_settings.
    # Modules that may fail to import (e.g. scheduler needs apscheduler)
    # use create=True so the patch succeeds even if the attribute can't be resolved.
    _always_patch = [
        "datapulse.core.config.get_settings",
        "datapulse.config.get_settings",
        "datapulse.import_pipeline.validator.get_settings",
        "datapulse.import_pipeline.reader.get_settings",
        "datapulse.bronze.loader.get_settings",
        "datapulse.api.deps.get_settings",
        "datapulse.api.auth.get_settings",
        "datapulse.embed.token.get_settings",
        "datapulse.api.routes.explore.get_settings",
        "datapulse.cache.get_settings",
    ]
    # Modules with heavy third-party deps that may not be importable in test env
    _optional_patch = [
        "datapulse.scheduler.get_settings",
        "datapulse.api.app.get_settings",  # may fail if email-validator not installed
    ]

    import contextlib

    always_patches = [patch(t, return_value=clean_settings) for t in _always_patch]
    optional_patches = [patch(t, return_value=clean_settings) for t in _optional_patch]

    with contextlib.ExitStack() as stack:
        for p in always_patches:
            stack.enter_context(p)
        for p in optional_patches:
            with contextlib.suppress(AttributeError, ModuleNotFoundError, ImportError):
                stack.enter_context(p)
        yield

    get_settings.cache_clear()


# --- Analytics fixtures ---


@pytest.fixture()
def mock_session():
    """Mock SQLAlchemy Session for repository tests."""
    session = MagicMock()
    return session


@pytest.fixture()
def analytics_repo(mock_session):
    """AnalyticsRepository with mocked session."""
    from datapulse.analytics.repository import AnalyticsRepository

    return AnalyticsRepository(mock_session)


@pytest.fixture()
def mock_repo():
    """Fully mocked AnalyticsRepository for service tests."""
    from datetime import date

    from datapulse.analytics.repository import AnalyticsRepository

    repo = create_autospec(AnalyticsRepository, instance=True)
    repo.get_data_date_range.return_value = (date(2023, 1, 1), date(2025, 3, 31))
    return repo


@pytest.fixture()
def mock_detail_repo():
    """Fully mocked DetailRepository for detail query tests."""
    from datapulse.analytics.detail_repository import DetailRepository

    return create_autospec(DetailRepository, instance=True)


@pytest.fixture()
def mock_breakdown_repo():
    """Fully mocked BreakdownRepository for breakdown tests."""
    from datapulse.analytics.breakdown_repository import BreakdownRepository

    return create_autospec(BreakdownRepository, instance=True)


@pytest.fixture()
def mock_comparison_repo():
    """Fully mocked ComparisonRepository for comparison tests."""
    from datapulse.analytics.comparison_repository import ComparisonRepository

    return create_autospec(ComparisonRepository, instance=True)


@pytest.fixture()
def mock_hierarchy_repo():
    """Fully mocked HierarchyRepository for hierarchy tests."""
    from datapulse.analytics.hierarchy_repository import HierarchyRepository

    return create_autospec(HierarchyRepository, instance=True)


@pytest.fixture()
def analytics_service(
    mock_repo, mock_detail_repo, mock_breakdown_repo, mock_comparison_repo, mock_hierarchy_repo
):
    """AnalyticsService with mocked repositories."""
    from datapulse.analytics.service import AnalyticsService

    return AnalyticsService(
        mock_repo, mock_detail_repo, mock_breakdown_repo, mock_comparison_repo, mock_hierarchy_repo
    )


@pytest.fixture()
def api_client():
    """FastAPI TestClient with mocked dependencies."""
    from datetime import date

    from fastapi.testclient import TestClient

    from datapulse.analytics.breakdown_repository import BreakdownRepository
    from datapulse.analytics.comparison_repository import ComparisonRepository
    from datapulse.analytics.detail_repository import DetailRepository
    from datapulse.analytics.hierarchy_repository import HierarchyRepository
    from datapulse.analytics.repository import AnalyticsRepository
    from datapulse.analytics.service import AnalyticsService

    mock_session = MagicMock()
    mock_repo = create_autospec(AnalyticsRepository, instance=True)
    mock_repo.get_data_date_range.return_value = (date(2023, 1, 1), date(2025, 3, 31))
    mock_detail_repo = create_autospec(DetailRepository, instance=True)
    mock_breakdown_repo = create_autospec(BreakdownRepository, instance=True)
    mock_comparison_repo = create_autospec(ComparisonRepository, instance=True)
    mock_hierarchy_repo = create_autospec(HierarchyRepository, instance=True)
    mock_svc = AnalyticsService(
        mock_repo, mock_detail_repo, mock_breakdown_repo, mock_comparison_repo, mock_hierarchy_repo
    )

    from datapulse.api import deps
    from datapulse.api.app import create_app
    from datapulse.api.auth import get_current_user

    _dev_user = {
        "sub": "test-user",
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["admin"],
        "raw_claims": {},
    }

    app = create_app()
    app.dependency_overrides[deps.get_tenant_session] = lambda: mock_session
    app.dependency_overrides[deps.get_analytics_service] = lambda: mock_svc
    app.dependency_overrides[get_current_user] = lambda: _dev_user

    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    yield client, mock_repo, mock_detail_repo

    app.dependency_overrides.clear()


# --- Pipeline fixtures ---


@pytest.fixture()
def pipeline_repo(mock_session):
    """PipelineRepository with mocked session."""
    from datapulse.pipeline.repository import PipelineRepository

    return PipelineRepository(mock_session)


@pytest.fixture()
def mock_pipeline_repo():
    """Fully mocked PipelineRepository for service tests."""
    from datapulse.pipeline.repository import PipelineRepository

    return create_autospec(PipelineRepository, instance=True)


@pytest.fixture()
def pipeline_service(mock_pipeline_repo):
    """PipelineService with mocked repository."""
    from datapulse.pipeline.service import PipelineService

    return PipelineService(mock_pipeline_repo)


@pytest.fixture()
def pipeline_api_client():
    """FastAPI TestClient with mocked pipeline dependencies."""
    from fastapi.testclient import TestClient

    from datapulse.api.auth import get_current_user
    from datapulse.pipeline.repository import PipelineRepository
    from datapulse.pipeline.service import PipelineService

    _dev_user = {
        "sub": "test-user",
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["admin"],
        "raw_claims": {},
    }

    mock_session = MagicMock()
    mock_pl_repo = create_autospec(PipelineRepository, instance=True)
    mock_pl_svc = PipelineService(mock_pl_repo)

    from datapulse.api import deps
    from datapulse.api.app import create_app

    app = create_app()
    app.dependency_overrides[deps.get_tenant_session] = lambda: mock_session
    app.dependency_overrides[deps.get_pipeline_service] = lambda: mock_pl_svc
    app.dependency_overrides[get_current_user] = lambda: _dev_user

    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    yield client, mock_pl_repo

    app.dependency_overrides.clear()
