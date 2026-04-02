"""Tests for structured logging module."""

from __future__ import annotations

from datapulse.logging import _mask_sensitive_fields, get_logger, setup_logging


class TestMaskSensitiveFields:
    def test_masks_password(self):
        event = {"event": "login", "password": "secret123"}
        result = _mask_sensitive_fields(None, "info", event)
        assert result["password"] == "***REDACTED***"

    def test_masks_api_key(self):
        event = {"event": "call", "api_key": "sk-123"}
        result = _mask_sensitive_fields(None, "info", event)
        assert result["api_key"] == "***REDACTED***"

    def test_masks_database_url(self):
        event = {"database_url": "postgresql://user:pass@host/db"}
        result = _mask_sensitive_fields(None, "info", event)
        assert result["database_url"] == "***REDACTED***"

    def test_leaves_non_sensitive_fields(self):
        event = {"event": "query", "table": "sales", "rows": 100}
        result = _mask_sensitive_fields(None, "info", event)
        assert result["table"] == "sales"
        assert result["rows"] == 100

    def test_masks_multiple_sensitive_keys(self):
        event = {"token": "abc", "secret": "xyz", "event": "test"}
        result = _mask_sensitive_fields(None, "info", event)
        assert result["token"] == "***REDACTED***"
        assert result["secret"] == "***REDACTED***"
        assert result["event"] == "test"


class TestSetupLogging:
    def test_setup_console_format(self):
        setup_logging(log_level="INFO", log_format="console")
        # Should not raise

    def test_setup_json_format(self):
        setup_logging(log_level="DEBUG", log_format="json")
        # Should not raise


class TestGetLogger:
    def test_returns_logger(self):
        logger = get_logger("test_module")
        assert logger is not None

    def test_returns_bound_logger(self):
        logger = get_logger("datapulse.api")
        # Should be a structlog FilteringBoundLogger
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
