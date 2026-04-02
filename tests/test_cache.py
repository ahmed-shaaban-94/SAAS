"""Tests for Redis cache module with graceful degradation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import datapulse.cache as cache_mod
from datapulse.cache import cache_get, cache_invalidate_pattern, cache_set, get_redis_client


@pytest.fixture(autouse=True)
def _reset_cache_state():
    """Reset module-level state before each test."""
    cache_mod._redis_client = None
    cache_mod._last_attempt = 0
    yield
    cache_mod._redis_client = None
    cache_mod._last_attempt = 0


class TestGetRedisClient:
    @patch("datapulse.cache.get_settings")
    def test_returns_none_when_no_url(self, mock_settings):
        mock_settings.return_value.redis_url = ""
        assert get_redis_client() is None

    @patch("datapulse.cache.get_settings")
    def test_returns_client_on_success(self, mock_settings):
        mock_settings.return_value.redis_url = "redis://localhost:6379/0"
        mock_client = MagicMock()
        with patch("redis.from_url", return_value=mock_client):
            mock_client.ping.return_value = True
            result = get_redis_client()
            assert result is mock_client

    @patch("datapulse.cache.get_settings")
    def test_returns_none_on_connection_error(self, mock_settings):
        mock_settings.return_value.redis_url = "redis://localhost:6379/0"
        with patch("redis.from_url", side_effect=Exception("Connection refused")):
            result = get_redis_client()
            assert result is None

    @patch("datapulse.cache.get_settings")
    def test_retry_interval_respected(self, mock_settings):
        import time

        mock_settings.return_value.redis_url = "redis://localhost:6379/0"
        with patch("redis.from_url", side_effect=Exception("fail")):
            get_redis_client()  # First attempt fails

        # Second attempt within retry interval should return None without trying
        cache_mod._last_attempt = time.monotonic()
        result = get_redis_client()
        assert result is None

    def test_returns_cached_client(self):
        mock_client = MagicMock()
        cache_mod._redis_client = mock_client
        assert get_redis_client() is mock_client


class TestCacheGet:
    def test_returns_none_when_no_client(self):
        assert cache_get("key") is None

    def test_returns_deserialized_value(self):
        mock_client = MagicMock()
        mock_client.get.return_value = json.dumps({"value": 42})
        cache_mod._redis_client = mock_client

        result = cache_get("key")
        assert result == {"value": 42}

    def test_returns_none_on_miss(self):
        mock_client = MagicMock()
        mock_client.get.return_value = None
        cache_mod._redis_client = mock_client

        assert cache_get("missing") is None

    def test_returns_none_on_error(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Redis error")
        cache_mod._redis_client = mock_client

        assert cache_get("key") is None


class TestCacheSet:
    def test_no_op_when_no_client(self):
        cache_set("key", "value")  # Should not raise

    @patch("datapulse.cache.get_settings")
    def test_sets_value_with_ttl(self, mock_settings):
        mock_settings.return_value.redis_default_ttl = 300
        mock_client = MagicMock()
        cache_mod._redis_client = mock_client

        cache_set("key", {"data": 1}, ttl=60)
        mock_client.setex.assert_called_once()
        args = mock_client.setex.call_args[0]
        assert args[0] == "key"
        assert args[1] == 60

    @patch("datapulse.cache.get_settings")
    def test_uses_default_ttl(self, mock_settings):
        mock_settings.return_value.redis_default_ttl = 300
        mock_client = MagicMock()
        cache_mod._redis_client = mock_client

        cache_set("key", "value")
        args = mock_client.setex.call_args[0]
        assert args[1] == 300

    def test_silently_fails_on_error(self):
        mock_client = MagicMock()
        mock_client.setex.side_effect = Exception("Redis error")
        cache_mod._redis_client = mock_client

        cache_set("key", "value", ttl=60)  # Should not raise


class TestCacheInvalidatePattern:
    def test_returns_zero_when_no_client(self):
        assert cache_invalidate_pattern("*") == 0

    def test_deletes_matching_keys(self):
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = ["key:1", "key:2"]
        mock_client.delete.return_value = 2
        cache_mod._redis_client = mock_client

        result = cache_invalidate_pattern("key:*")
        assert result == 2

    def test_returns_zero_when_no_matches(self):
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = []
        cache_mod._redis_client = mock_client

        assert cache_invalidate_pattern("nomatch:*") == 0

    def test_returns_zero_on_error(self):
        mock_client = MagicMock()
        mock_client.scan_iter.side_effect = Exception("Redis error")
        cache_mod._redis_client = mock_client

        assert cache_invalidate_pattern("*") == 0
