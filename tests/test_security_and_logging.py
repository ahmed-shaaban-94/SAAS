"""Tests for security, logging, and config utilities."""

import pytest

from datapulse.core.config import Settings
from datapulse.core.security import compare_secrets
from datapulse.logging import _mask_sensitive_fields, setup_logging
from datapulse.pipeline.models import PipelineRunCreate


def _settings(**overrides) -> Settings:
    overrides.setdefault("database_url", "")
    return Settings(_env_file=None, **overrides)


def test_compare_secrets_match():
    assert compare_secrets("my-secret", "my-secret") is True


def test_compare_secrets_mismatch():
    assert compare_secrets("my-secret", "other-secret") is False


def test_compare_secrets_empty():
    assert compare_secrets("", "") is True


def test_mask_sensitive_fields_redacts():
    event = {"event": "login", "password": "hunter2", "token": "abc123"}
    result = _mask_sensitive_fields(None, "info", event)
    assert result["password"] == "***REDACTED***"
    assert result["token"] == "***REDACTED***"
    assert result["event"] == "login"


def test_mask_sensitive_fields_no_sensitive():
    event = {"event": "request", "method": "GET"}
    result = _mask_sensitive_fields(None, "info", event)
    assert result == {"event": "request", "method": "GET"}


def test_setup_logging_json():
    """setup_logging with json format does not raise."""
    setup_logging(log_level="WARNING", log_format="json")


def test_setup_logging_console():
    """setup_logging with console format does not raise."""
    setup_logging(log_level="INFO", log_format="console")


def test_auth0_issuer_url():
    s = _settings(auth0_domain="test.us.auth0.com")
    assert s.auth0_issuer_url == "https://test.us.auth0.com/"


def test_auth0_jwks_url():
    s = _settings(auth0_domain="test.us.auth0.com")
    assert s.auth0_jwks_url == "https://test.us.auth0.com/.well-known/jwks.json"


def test_pipeline_run_create_invalid_run_type():
    """PipelineRunCreate rejects invalid run_type."""
    with pytest.raises(Exception, match="Invalid run_type"):
        PipelineRunCreate(run_type="invalid_type")
