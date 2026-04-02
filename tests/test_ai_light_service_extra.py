"""Extra tests for AI-Light service — covering uncovered paths."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch


class TestAILightServiceAvailability:
    @patch("datapulse.ai_light.service.OpenRouterClient")
    @patch("datapulse.ai_light.service.AnalyticsRepository")
    def test_is_available_when_configured(self, mock_repo_cls, mock_client_cls):
        from datapulse.ai_light.service import AILightService

        mock_client = MagicMock()
        type(mock_client).is_configured = PropertyMock(return_value=True)
        mock_client_cls.return_value = mock_client

        svc = AILightService(settings=MagicMock(), session=MagicMock())
        assert svc.is_available is True

    @patch("datapulse.ai_light.service.OpenRouterClient")
    @patch("datapulse.ai_light.service.AnalyticsRepository")
    def test_is_not_available_when_not_configured(self, mock_repo_cls, mock_client_cls):
        from datapulse.ai_light.service import AILightService

        mock_client = MagicMock()
        type(mock_client).is_configured = PropertyMock(return_value=False)
        mock_client_cls.return_value = mock_client

        svc = AILightService(settings=MagicMock(), session=MagicMock())
        assert svc.is_available is False
