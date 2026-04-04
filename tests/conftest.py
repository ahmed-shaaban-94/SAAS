"""Session-scoped test configuration for DataPulse.

Problem: The project's .env file contains extra keys (POSTGRES_USER,
POSTGRES_PASSWORD, POSTGRES_DB, PGADMIN_EMAIL, PGADMIN_PASSWORD) that
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
    """Set minimal env vars so modules with eager Settings() calls can import.

    This runs before test collection, fixing collection errors in modules
    that call get_settings() at module level.
    """
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")


from datapulse.api.limiter import limiter  # noqa: E402
from datapulse.config import Settings, get_settings  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _disable_rate_limiting():
    """Disable rate limiting for all tests."""
    limiter.enabled = False
    yield
    limiter.enabled = True


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

    # Also patch the imported references in each module that uses get_settings
    with (
        patch("datapulse.core.config.get_settings", return_value=clean_settings),
        patch("datapulse.config.get_settings", return_value=clean_settings),
        patch("datapulse.import_pipeline.validator.get_settings", return_value=clean_settings),
        patch("datapulse.import_pipeline.reader.get_settings", return_value=clean_settings),
        patch("datapulse.bronze.loader.get_settings", return_value=clean_settings),
        patch("datapulse.api.deps.get_settings", return_value=clean_settings),
        patch("datapulse.api.app.get_settings", return_value=clean_settings),
        patch("datapulse.api.auth.get_settings", return_value=clean_settings),
        patch("datapulse.embed.token.get_settings", return_value=clean_settings),
        patch("datapulse.api.routes.explore.get_settings", return_value=clean_settings),
        patch("datapulse.scheduler.get_settings", return_value=clean_settings),
        patch("datapulse.cache.get_settings", return_value=clean_settings),
    ):
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
    app.dependency_overrides[deps.get_db_session] = lambda: mock_session
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
    app.dependency_overrides[deps.get_db_session] = lambda: mock_session
    app.dependency_overrides[deps.get_tenant_session] = lambda: mock_session
    app.dependency_overrides[deps.get_pipeline_service] = lambda: mock_pl_svc
    app.dependency_overrides[get_current_user] = lambda: _dev_user

    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    yield client, mock_pl_repo

    app.dependency_overrides.clear()
