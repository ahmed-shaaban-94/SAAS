"""Tests for datapulse.api.deps — dependency injection factories."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

from datapulse.api.deps import (
    get_ai_light_service,
    get_analytics_service,
    get_db_session,
    get_forecasting_service,
    get_pipeline_executor,
    get_pipeline_service,
    get_quality_service,
    get_tenant_session,
)


class TestGetDbSession:
    @patch("datapulse.api.deps.get_session_factory")
    def test_yields_session_and_commits(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        gen = get_db_session()
        session = next(gen)

        assert session is mock_session
        assert mock_session.execute.call_count == 2  # SET LOCAL tenant_id + statement_timeout

        # Exhaust generator (finally block)
        with contextlib.suppress(StopIteration):
            next(gen)

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("datapulse.api.deps.get_session_factory")
    def test_rollback_on_exception(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        gen = get_db_session()
        next(gen)  # get session

        # Simulate an exception during request handling
        with contextlib.suppress(ValueError):
            gen.throw(ValueError("test error"))

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()


class TestGetTenantSession:
    @patch("datapulse.core.auth.get_session_factory")
    def test_sets_tenant_id_from_user(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        user = {"tenant_id": "42", "sub": "test"}

        gen = get_tenant_session(user=user)
        session = next(gen)

        assert session is mock_session
        # Verify SET LOCAL was called with tenant_id and statement_timeout
        assert mock_session.execute.call_count == 2
        tenant_call = mock_session.execute.call_args_list[0]
        assert tenant_call.args[1] == {"tid": "42"}
        timeout_call = mock_session.execute.call_args_list[1]
        assert "statement_timeout" in timeout_call.args[0].text

        with contextlib.suppress(StopIteration):
            next(gen)

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("datapulse.core.auth.get_session_factory")
    def test_defaults_tenant_id_to_1(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        user = {"sub": "test"}  # no tenant_id

        gen = get_tenant_session(user=user)
        next(gen)

        tenant_call = mock_session.execute.call_args_list[0]
        assert tenant_call.args[1] == {"tid": "1"}

        with contextlib.suppress(StopIteration):
            next(gen)

    @patch("datapulse.core.auth.get_session_factory")
    def test_rollback_on_exception(self, mock_factory):
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        user = {"tenant_id": "1"}

        gen = get_tenant_session(user=user)
        next(gen)

        with contextlib.suppress(RuntimeError):
            gen.throw(RuntimeError("db error"))

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestFactoryFunctions:
    def test_get_analytics_service(self):
        mock_session = MagicMock()
        svc = get_analytics_service(session=mock_session)
        from datapulse.analytics.service import AnalyticsService

        assert isinstance(svc, AnalyticsService)

    def test_get_pipeline_service(self):
        mock_session = MagicMock()
        svc = get_pipeline_service(session=mock_session)
        from datapulse.pipeline.service import PipelineService

        assert isinstance(svc, PipelineService)

    def test_get_pipeline_executor(self):
        executor = get_pipeline_executor()
        from datapulse.pipeline.executor import PipelineExecutor

        assert isinstance(executor, PipelineExecutor)

    def test_get_quality_service(self):
        mock_session = MagicMock()
        svc = get_quality_service(session=mock_session)
        from datapulse.pipeline.quality_service import QualityService

        assert isinstance(svc, QualityService)

    def test_get_forecasting_service(self):
        mock_session = MagicMock()
        svc = get_forecasting_service(session=mock_session)
        from datapulse.forecasting.service import ForecastingService

        assert isinstance(svc, ForecastingService)

    def test_get_ai_light_service(self):
        mock_session = MagicMock()
        svc = get_ai_light_service(session=mock_session)
        from datapulse.ai_light.service import AILightService

        assert isinstance(svc, AILightService)
