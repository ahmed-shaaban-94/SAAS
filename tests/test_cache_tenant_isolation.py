"""Tests for tenant-scoped cache key isolation.

Verifies that Redis cache keys include tenant_id to prevent
cross-tenant data leakage (MT1 finding from Session 8 audit).
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

from datapulse.cache import current_tenant_id
from datapulse.cache_decorator import _build_cache_key, cached


class _FakeSelf:
    pass


def _expected_hash(parts: dict) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]


class TestCacheKeyTenantIsolation:
    """Cache keys MUST include tenant_id to prevent cross-tenant leakage."""

    def test_different_tenants_produce_different_keys(self):
        """Two tenants making the same query must get different cache keys."""
        token = current_tenant_id.set("1")
        try:
            key_t1 = _build_cache_key("analytics", "summary", (), {})
        finally:
            current_tenant_id.reset(token)

        token = current_tenant_id.set("2")
        try:
            key_t2 = _build_cache_key("analytics", "summary", (), {})
        finally:
            current_tenant_id.reset(token)

        assert key_t1 != key_t2
        assert "t1" in key_t1
        assert "t2" in key_t2

    def test_same_tenant_produces_same_key(self):
        """Same tenant with same args must produce the same cache key."""
        token = current_tenant_id.set("5")
        try:
            key1 = _build_cache_key("p", "m", (), {"limit": 10})
            key2 = _build_cache_key("p", "m", (), {"limit": 10})
        finally:
            current_tenant_id.reset(token)

        assert key1 == key2

    def test_tenant_segment_in_key_format(self):
        """Cache key must contain t{tenant_id} segment."""
        token = current_tenant_id.set("42")
        try:
            key = _build_cache_key("pfx", "method", (), {})
        finally:
            current_tenant_id.reset(token)

        assert key == "pfx:t42:method"

    def test_tenant_segment_with_args(self):
        """Tenant segment present even with hashed args."""
        token = current_tenant_id.set("7")
        try:
            key = _build_cache_key("p", "m", (_FakeSelf(), "val"), {})
        finally:
            current_tenant_id.reset(token)

        expected_parts = {"arg0": "val"}
        h = _expected_hash(expected_parts)
        assert key == f"p:t7:m:{h}"

    def test_empty_tenant_uses_t0_fallback(self):
        """When tenant_id is not set, key uses t0 as a safe default."""
        token = current_tenant_id.set("")
        try:
            key = _build_cache_key("p", "m", (), {})
        finally:
            current_tenant_id.reset(token)

        assert key == "p:t0:m"


class TestAnalyticsCacheKeyTenantIsolation:
    """Verify the manual _cache_key in analytics/service.py is tenant-scoped."""

    def test_analytics_cache_key_includes_tenant(self):
        from datapulse.analytics.service import _cache_key

        token = current_tenant_id.set("3")
        try:
            key = _cache_key("summary")
        finally:
            current_tenant_id.reset(token)

        assert "t3" in key
        assert key.startswith("datapulse:analytics:t3:summary")

    def test_analytics_different_tenants_different_keys(self):
        from datapulse.analytics.service import _cache_key

        token = current_tenant_id.set("1")
        try:
            key1 = _cache_key("trends", {"start": "2024-01-01"})
        finally:
            current_tenant_id.reset(token)

        token = current_tenant_id.set("2")
        try:
            key2 = _cache_key("trends", {"start": "2024-01-01"})
        finally:
            current_tenant_id.reset(token)

        assert key1 != key2


class TestCachedDecoratorTenantIsolation:
    """The @cached decorator must produce tenant-scoped keys."""

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_decorator_cache_key_includes_tenant(self, mock_get, mock_set):
        mock_get.return_value = None

        @cached(ttl=60, prefix="test")
        def my_method(self_arg):
            return {"data": 1}

        token = current_tenant_id.set("99")
        try:
            my_method("self")
        finally:
            current_tenant_id.reset(token)

        cache_key = mock_get.call_args[0][0]
        assert "t99" in cache_key

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_decorator_different_tenants_different_keys(self, mock_get, mock_set):
        mock_get.return_value = None

        @cached(ttl=60, prefix="svc")
        def get_data(self_arg, x):
            return {"value": x}

        token = current_tenant_id.set("1")
        try:
            get_data("self", 10)
        finally:
            current_tenant_id.reset(token)

        key1 = mock_get.call_args[0][0]

        token = current_tenant_id.set("2")
        try:
            get_data("self", 10)
        finally:
            current_tenant_id.reset(token)

        key2 = mock_get.call_args[0][0]

        assert key1 != key2
        assert "t1" in key1
        assert "t2" in key2
