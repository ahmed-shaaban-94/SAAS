"""Tests for datapulse.api.deps — dependency injection factories."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest

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
    def test_missing_tenant_id_is_contract_violation(self, mock_factory):
        """A user dict reaching ``get_tenant_session`` without ``tenant_id`` is a
        programming error — ``get_current_user`` is contractually required to
        populate it (or 401 upstream — see #546). The dead ``or "1"`` fallback
        was silently routing to tenant 1 when the upstream contract was
        violated, which is exactly the bug the audit flagged.
        """
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        user = {"sub": "test"}  # no tenant_id — upstream contract violated

        gen = get_tenant_session(user=user)
        with pytest.raises(KeyError, match="tenant_id"):
            next(gen)

        # The session must not be opened when the contract is violated.
        mock_factory.assert_not_called()

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


class TestGetTenantSessionReadonly:
    """Mirror of TestGetTenantSession — the read-replica session function
    has the same M1 contract: ``get_current_user`` guarantees ``tenant_id``,
    so the previous ``or "1"`` fallback was dead and now raises KeyError
    on programming-error paths.
    """

    @patch("datapulse.core.auth.get_readonly_session_factory")
    @patch("datapulse.core.auth.get_session_factory")
    @patch("datapulse.core.auth.get_settings")
    def test_missing_tenant_id_is_contract_violation(
        self, mock_get_settings, mock_factory, mock_readonly_factory
    ):
        from datapulse.core.auth import get_tenant_session_readonly

        mock_get_settings.return_value = MagicMock(database_replica_url="")
        user = {"sub": "test"}  # no tenant_id — upstream contract violated

        gen = get_tenant_session_readonly(user=user)
        with pytest.raises(KeyError, match="tenant_id"):
            next(gen)

        # No session opened on a programming-error path.
        mock_factory.assert_not_called()
        mock_readonly_factory.assert_not_called()


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

    def test_get_pos_service_uses_pharmacist_signing_secret(self):
        """Audit C2: PharmacistVerifier must derive its HMAC key from
        ``pharmacist_signing_secret``, not ``pipeline_webhook_secret``.
        Sharing the secret coupled two unrelated threat models — see config
        comment for the full rationale."""
        from datapulse.api.deps import get_pos_service
        from datapulse.config import Settings

        mock_session = MagicMock()
        # Distinct values so we can prove which one was picked.
        test_settings = Settings(
            _env_file=None,
            database_url="",
            pipeline_webhook_secret="WRONG_PIPELINE_SECRET",
            pharmacist_signing_secret="CORRECT_PHARMACIST_SECRET",
        )
        with patch("datapulse.api.deps.get_settings", return_value=test_settings):
            svc = get_pos_service(
                session=mock_session,
                user={"tenant_id": "1", "sub": "test"},
            )

        assert svc._verifier.secret_key == "CORRECT_PHARMACIST_SECRET"
