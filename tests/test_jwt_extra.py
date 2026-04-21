"""Extra tests for JWT module — covers _get_signing_key function (lines 57-100)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from datapulse.api.jwt import _get_signing_key, clear_jwks_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_jwks_cache()
    yield
    clear_jwks_cache()


@pytest.fixture()
def mock_settings() -> MagicMock:
    s = MagicMock()
    s.auth0_jwks_url = "https://test.auth0.com/.well-known/jwks.json"
    s.auth0_issuer_url = "https://test.auth0.com/"
    s.auth0_audience = "https://api.test.com"
    s.auth0_client_id = "test-client-id"
    return s


class TestGetSigningKey:
    @patch("datapulse.core.jwt._fetch_jwks")
    def test_jwks_parse_error(self, mock_fetch, mock_settings):
        """When PyJWKSet.from_dict fails, should raise 503."""
        mock_fetch.return_value = {"keys": []}  # empty keys -> parse error

        # PyJWKSet.from_dict with empty keys raises PyJWKSetError
        with patch("datapulse.core.jwt.jwt.PyJWKSet.from_dict") as mock_jwk_set:
            mock_jwk_set.side_effect = pyjwt.PyJWKSetError("no keys")
            with pytest.raises(HTTPException) as exc:
                _get_signing_key("some-token", mock_settings)
            assert exc.value.status_code == 503

    @patch("datapulse.core.jwt._fetch_jwks")
    def test_invalid_token_format(self, mock_fetch, mock_settings):
        """When token header can't be decoded, should raise 401."""
        mock_fetch.return_value = {"keys": [{"kid": "k1", "kty": "RSA", "n": "abc", "e": "AQAB"}]}

        mock_jwk = MagicMock()
        mock_jwk.key_id = "k1"
        mock_jwk_set = MagicMock()
        mock_jwk_set.keys = [mock_jwk]

        with (
            patch("datapulse.core.jwt.jwt.PyJWKSet.from_dict", return_value=mock_jwk_set),
            patch(
                "datapulse.core.jwt.jwt.get_unverified_header",
                side_effect=pyjwt.DecodeError("bad token"),
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                _get_signing_key("garbage-token", mock_settings)
            assert exc.value.status_code == 401
            assert "Invalid token format" in exc.value.detail

    @patch("datapulse.core.jwt._fetch_jwks")
    def test_token_missing_kid(self, mock_fetch, mock_settings):
        """When token header has no kid, should raise 401."""
        mock_fetch.return_value = {"keys": [{"kid": "k1", "kty": "RSA"}]}

        mock_jwk = MagicMock()
        mock_jwk.key_id = "k1"
        mock_jwk_set = MagicMock()
        mock_jwk_set.keys = [mock_jwk]

        with (
            patch("datapulse.core.jwt.jwt.PyJWKSet.from_dict", return_value=mock_jwk_set),
            patch(
                "datapulse.core.jwt.jwt.get_unverified_header",
                return_value={"alg": "RS256"},  # no kid
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                _get_signing_key("no-kid-token", mock_settings)
            assert exc.value.status_code == 401
            assert "missing key ID" in exc.value.detail

    @patch("datapulse.core.jwt._fetch_jwks")
    def test_key_found_on_first_try(self, mock_fetch, mock_settings):
        """When kid matches on first try, returns the key."""
        mock_fetch.return_value = {"keys": [{"kid": "match-kid"}]}

        mock_jwk = MagicMock()
        mock_jwk.key_id = "match-kid"
        mock_jwk_set = MagicMock()
        mock_jwk_set.keys = [mock_jwk]

        with (
            patch("datapulse.core.jwt.jwt.PyJWKSet.from_dict", return_value=mock_jwk_set),
            patch(
                "datapulse.core.jwt.jwt.get_unverified_header",
                return_value={"kid": "match-kid", "alg": "RS256"},
            ),
        ):
            result = _get_signing_key("good-token", mock_settings)
            assert result.key_id == "match-kid"

    @patch("datapulse.core.jwt._fetch_jwks")
    def test_key_found_after_cache_refresh(self, mock_fetch, mock_settings):
        """When kid not found initially, clears cache and retries."""
        mock_jwk_old = MagicMock()
        mock_jwk_old.key_id = "old-kid"
        mock_jwk_set_old = MagicMock()
        mock_jwk_set_old.keys = [mock_jwk_old]

        mock_jwk_new = MagicMock()
        mock_jwk_new.key_id = "new-kid"
        mock_jwk_set_new = MagicMock()
        mock_jwk_set_new.keys = [mock_jwk_new]

        # First fetch returns old keys, second (after cache clear) returns new
        mock_fetch.side_effect = [
            {"keys": [{"kid": "old-kid"}]},
            {"keys": [{"kid": "new-kid"}]},
        ]

        with (
            patch(
                "datapulse.core.jwt.jwt.PyJWKSet.from_dict",
                side_effect=[mock_jwk_set_old, mock_jwk_set_new],
            ),
            patch(
                "datapulse.core.jwt.jwt.get_unverified_header",
                return_value={"kid": "new-kid", "alg": "RS256"},
            ),
        ):
            result = _get_signing_key("token-with-new-kid", mock_settings)
            assert result.key_id == "new-kid"
            assert mock_fetch.call_count == 2

    @patch("datapulse.core.jwt._fetch_jwks")
    def test_key_not_found_after_retry(self, mock_fetch, mock_settings):
        """When kid not found even after cache refresh, raises 401."""
        mock_jwk = MagicMock()
        mock_jwk.key_id = "wrong-kid"
        mock_jwk_set = MagicMock()
        mock_jwk_set.keys = [mock_jwk]

        mock_fetch.return_value = {"keys": [{"kid": "wrong-kid"}]}

        with (
            patch("datapulse.core.jwt.jwt.PyJWKSet.from_dict", return_value=mock_jwk_set),
            patch(
                "datapulse.core.jwt.jwt.get_unverified_header",
                return_value={"kid": "missing-kid", "alg": "RS256"},
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                _get_signing_key("token", mock_settings)
            assert exc.value.status_code == 401
            assert "signing key not found" in exc.value.detail

    @patch("datapulse.core.jwt._fetch_jwks")
    def test_retry_jwks_parse_error(self, mock_fetch, mock_settings):
        """When second parse after cache refresh fails, raises 503."""
        mock_jwk_old = MagicMock()
        mock_jwk_old.key_id = "old-kid"
        mock_jwk_set_old = MagicMock()
        mock_jwk_set_old.keys = [mock_jwk_old]

        mock_fetch.side_effect = [
            {"keys": [{"kid": "old-kid"}]},
            {"keys": []},
        ]

        with (
            patch(
                "datapulse.core.jwt.jwt.PyJWKSet.from_dict",
                side_effect=[mock_jwk_set_old, pyjwt.PyJWKSetError("bad keys")],
            ),
            patch(
                "datapulse.core.jwt.jwt.get_unverified_header",
                return_value={"kid": "new-kid", "alg": "RS256"},
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                _get_signing_key("token", mock_settings)
            assert exc.value.status_code == 503
