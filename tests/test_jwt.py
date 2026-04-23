"""Tests for JWT verification module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from datapulse.api.jwt import _fetch_jwks, clear_jwks_cache, verify_jwt


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear JWKS cache before each test."""
    clear_jwks_cache()
    yield
    clear_jwks_cache()


@pytest.fixture()
def mock_settings() -> MagicMock:
    """Default Settings stub — Clerk values with explicit audience + azp for
    tests that exercise aud/azp verification paths.
    """
    s = MagicMock()
    s.auth_provider = "clerk"
    s.active_jwks_url = "https://test.clerk.accounts.dev/.well-known/jwks.json"
    s.active_issuer_url = "https://test.clerk.accounts.dev"
    s.active_audience = "https://api.test.com"
    s.active_expected_azp = "test-client-id"
    return s


@pytest.fixture()
def mock_clerk_settings() -> MagicMock:
    """Settings stub mimicking AUTH_PROVIDER=clerk — no ``aud``/``azp``."""
    s = MagicMock()
    s.auth_provider = "clerk"
    s.active_jwks_url = "https://example.clerk.accounts.dev/.well-known/jwks.json"
    s.active_issuer_url = "https://example.clerk.accounts.dev"
    s.active_audience = ""
    s.active_expected_azp = ""
    return s


class TestFetchJWKS:
    @patch("datapulse.core.jwt.httpx.get")
    def test_fetch_jwks_success(self, mock_get, mock_settings):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": [{"kid": "key1"}]}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = _fetch_jwks(mock_settings)
        assert result["keys"][0]["kid"] == "key1"

    @patch("datapulse.core.jwt.httpx.get")
    def test_fetch_jwks_cached(self, mock_get, mock_settings):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        _fetch_jwks(mock_settings)
        _fetch_jwks(mock_settings)
        # Should only call httpx once (cached)
        assert mock_get.call_count == 1

    @patch("datapulse.core.jwt.httpx.get")
    def test_fetch_jwks_failure_no_cache(self, mock_get, mock_settings):
        import httpx

        mock_get.side_effect = httpx.TransportError("Connection refused")

        with pytest.raises(HTTPException) as exc:
            _fetch_jwks(mock_settings)
        assert exc.value.status_code == 503

    @patch("datapulse.core.jwt.httpx.get")
    def test_fetch_jwks_failure_returns_stale_cache(self, mock_get, mock_settings):
        import httpx

        # First call succeeds
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": [{"kid": "stale"}]}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        _fetch_jwks(mock_settings)

        # Force cache expiry and make second call fail
        import datapulse.core.jwt as jwt_mod

        # The cache is keyed by JWKS URL and stores (data, timestamp);
        # reset the timestamp to 0 so the TTL check fails on the next call.
        url = mock_settings.active_jwks_url
        assert url in jwt_mod._jwks_cache
        data, _ = jwt_mod._jwks_cache[url]
        jwt_mod._jwks_cache[url] = (data, 0.0)
        mock_get.side_effect = httpx.TransportError("timeout")

        result = _fetch_jwks(mock_settings)
        assert result["keys"][0]["kid"] == "stale"


class TestVerifyJWT:
    @patch("datapulse.core.jwt.jwt.decode", side_effect=pyjwt.ExpiredSignatureError)
    @patch("datapulse.core.jwt._get_signing_key")
    def test_verify_jwt_expired(self, mock_key, mock_decode, mock_settings):
        mock_key.return_value = MagicMock(key="fake-key")
        with pytest.raises(HTTPException) as exc:
            verify_jwt("expired-token", settings=mock_settings)
        assert exc.value.status_code == 401
        assert "expired" in exc.value.detail.lower()

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_invalid_issuer(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.side_effect = pyjwt.InvalidIssuerError()

        with pytest.raises(HTTPException) as exc:
            verify_jwt("bad-token", settings=mock_settings)
        assert exc.value.status_code == 401

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_invalid_audience(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.side_effect = pyjwt.InvalidAudienceError()

        with pytest.raises(HTTPException) as exc:
            verify_jwt("bad-token", settings=mock_settings)
        assert exc.value.status_code == 401

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_success(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {
            "sub": "user-1",
            "email": "test@test.com",
            "azp": "test-client-id",
        }
        claims = verify_jwt("valid-token", settings=mock_settings)
        assert claims["sub"] == "user-1"

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_wrong_azp(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {
            "sub": "user-1",
            "azp": "wrong-client-id",
        }
        with pytest.raises(HTTPException) as exc:
            verify_jwt("token", settings=mock_settings)
        assert exc.value.status_code == 401
        assert "client" in exc.value.detail.lower()

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_no_azp_passes(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {"sub": "user-1"}
        claims = verify_jwt("token", settings=mock_settings)
        assert claims["sub"] == "user-1"


class TestVerifyJWTAzpEdgeCase:
    """Lock in the azp-skipped-when-empty behaviour."""

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_azp_check_skipped_when_expected_azp_empty(self, mock_decode, mock_key):
        """When ``active_expected_azp`` is empty, the azp check is skipped —
        prevents a future refactor from accidentally tightening this gate.
        """
        s = MagicMock()
        s.auth_provider = "clerk"
        s.active_jwks_url = "https://test.clerk.accounts.dev/.well-known/jwks.json"
        s.active_issuer_url = "https://test.clerk.accounts.dev"
        s.active_audience = ""
        s.active_expected_azp = ""
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {"sub": "user-1", "azp": "anything"}
        claims = verify_jwt("token", settings=s)
        assert claims["sub"] == "user-1"


class TestVerifyJWTClerk:
    """verify_jwt with AUTH_PROVIDER=clerk — skips ``aud`` and ``azp`` checks."""

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_clerk_skips_aud_verification(self, mock_decode, mock_key, mock_clerk_settings):
        """Clerk's default template has no ``aud`` claim, so we pass
        ``audience=None`` and ``verify_aud=False`` to pyjwt.
        """
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {"sub": "user_clerk_1", "email": "a@b"}
        claims = verify_jwt("clerk-token", settings=mock_clerk_settings)
        assert claims["sub"] == "user_clerk_1"

        # pyjwt was called with verify_aud=False and audience=None
        kwargs = mock_decode.call_args.kwargs
        assert kwargs["audience"] is None
        assert kwargs["options"]["verify_aud"] is False

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_clerk_skips_azp_even_when_present(self, mock_decode, mock_key, mock_clerk_settings):
        """Clerk puts its Frontend API URL in ``azp``. That's not a stable
        value we want to pin, so active_expected_azp is empty and the check
        is suppressed.
        """
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {
            "sub": "user_clerk_1",
            "azp": "https://something-else.clerk.accounts.dev",
        }
        # Would raise 401 if the azp check still fired for Clerk tokens
        claims = verify_jwt("clerk-token", settings=mock_clerk_settings)
        assert claims["sub"] == "user_clerk_1"


class TestClearCache:
    def test_clear_jwks_cache(self):
        """clear_jwks_cache empties the per-URL cache used by _fetch_jwks."""
        import datapulse.core.jwt as jwt_mod

        jwt_mod._jwks_cache["https://example.com/jwks"] = ({"keys": []}, 100.0)
        clear_jwks_cache()
        assert jwt_mod._jwks_cache == {}
