"""Tests for datapulse.cache_decorator module."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

from datapulse.cache_decorator import _build_cache_key, cached

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakePydanticModel:
    """Minimal stand-in for a Pydantic model with model_dump()."""

    def __init__(self, data: dict):
        self._data = data

    def model_dump(self, *, mode: str = "python") -> dict:
        return self._data


class _FakeSelf:
    """Placeholder for the `self` argument of a bound method."""


def _expected_hash(parts: dict) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]


# ===================================================================
# _build_cache_key
# ===================================================================


class TestBuildCacheKey:
    """Tests for _build_cache_key."""

    def test_no_args_returns_prefix_and_method(self):
        key = _build_cache_key("analytics", "get_summary", (), {})
        assert key == "analytics:get_summary"

    def test_self_is_skipped(self):
        """When the only positional arg is `self`, it should be skipped."""
        self_obj = _FakeSelf()
        key = _build_cache_key("pfx", "do_thing", (self_obj,), {})
        assert key == "pfx:do_thing"

    def test_positional_args_produce_consistent_hash(self):
        self_obj = _FakeSelf()
        key1 = _build_cache_key("p", "m", (self_obj, "a", 42), {})
        key2 = _build_cache_key("p", "m", (self_obj, "a", 42), {})
        assert key1 == key2

        expected_parts = {"arg0": "a", "arg1": 42}
        h = _expected_hash(expected_parts)
        assert key1 == f"p:m:{h}"

    def test_different_args_produce_different_keys(self):
        self_obj = _FakeSelf()
        key1 = _build_cache_key("p", "m", (self_obj, "a"), {})
        key2 = _build_cache_key("p", "m", (self_obj, "b"), {})
        assert key1 != key2

    def test_kwargs_produce_consistent_hash(self):
        key1 = _build_cache_key("p", "m", (), {"limit": 10, "offset": 0})
        key2 = _build_cache_key("p", "m", (), {"limit": 10, "offset": 0})
        assert key1 == key2

        h = _expected_hash({"limit": 10, "offset": 0})
        assert key1 == f"p:m:{h}"

    def test_kwargs_order_does_not_matter(self):
        key1 = _build_cache_key("p", "m", (), {"a": 1, "b": 2})
        key2 = _build_cache_key("p", "m", (), {"b": 2, "a": 1})
        assert key1 == key2

    def test_pydantic_model_positional_arg(self):
        model = _FakePydanticModel({"start": "2024-01-01", "end": "2024-12-31"})
        self_obj = _FakeSelf()
        key = _build_cache_key("a", "fn", (self_obj, model), {})

        expected_parts = {"arg0": {"start": "2024-01-01", "end": "2024-12-31"}}
        h = _expected_hash(expected_parts)
        assert key == f"a:fn:{h}"

    def test_pydantic_model_kwarg(self):
        model = _FakePydanticModel({"x": 1})
        key = _build_cache_key("a", "fn", (), {"filters": model})

        expected_parts = {"filters": {"x": 1}}
        h = _expected_hash(expected_parts)
        assert key == f"a:fn:{h}"

    def test_mixed_args_and_kwargs(self):
        self_obj = _FakeSelf()
        key = _build_cache_key("p", "m", (self_obj, "v1"), {"k": "v2"})

        expected_parts = {"arg0": "v1", "k": "v2"}
        h = _expected_hash(expected_parts)
        assert key == f"p:m:{h}"


# ===================================================================
# @cached decorator
# ===================================================================


class TestCachedDecorator:
    """Tests for the @cached decorator."""

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_cache_hit_returns_cached_value(self, mock_get, mock_set):
        mock_get.return_value = {"total": 100}

        @cached(ttl=60, prefix="test")
        def get_data(self_arg):
            raise AssertionError("Should not be called on cache hit")

        result = get_data("self_placeholder")
        assert result == {"total": 100}
        mock_get.assert_called_once()
        mock_set.assert_not_called()

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_cache_miss_calls_function_and_caches(self, mock_get, mock_set):
        mock_get.return_value = None
        call_count = 0

        @cached(ttl=120, prefix="svc")
        def compute(self_arg, x):
            nonlocal call_count
            call_count += 1
            return {"value": x * 2}

        result = compute("self", 5)
        assert result == {"value": 10}
        assert call_count == 1
        mock_set.assert_called_once()
        # Verify ttl is passed
        _, call_kwargs = mock_set.call_args
        assert call_kwargs["ttl"] == 120

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_pydantic_model_result_uses_model_dump(self, mock_get, mock_set):
        mock_get.return_value = None
        model = _FakePydanticModel({"revenue": 42.5})

        @cached(ttl=60, prefix="t")
        def get_model(self_arg):
            return model

        result = get_model("self")
        assert result is model  # original object returned to caller

        # cache_set should receive the dict from model_dump(mode="json")
        set_args = mock_set.call_args
        assert set_args[0][1] == {"revenue": 42.5}
        assert set_args[1]["ttl"] == 60

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_dict_result_cached_directly(self, mock_get, mock_set):
        mock_get.return_value = None

        @cached(ttl=30, prefix="t")
        def get_dict(self_arg):
            return {"key": "val"}

        get_dict("self")
        assert mock_set.call_args[0][1] == {"key": "val"}

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_list_result_cached_directly(self, mock_get, mock_set):
        mock_get.return_value = None

        @cached(ttl=30, prefix="t")
        def get_list(self_arg):
            return [1, 2, 3]

        get_list("self")
        assert mock_set.call_args[0][1] == [1, 2, 3]

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_tuple_result_cached_as_list(self, mock_get, mock_set):
        mock_get.return_value = None

        @cached(ttl=30, prefix="t")
        def get_tuple(self_arg):
            return (1, 2, 3)

        result = get_tuple("self")
        assert result == (1, 2, 3)  # caller gets original tuple
        assert mock_set.call_args[0][1] == [1, 2, 3]  # cached as list

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_primitive_results_cached(self, mock_get, mock_set):
        mock_get.return_value = None

        @cached(ttl=10, prefix="t")
        def get_int(self_arg):
            return 42

        get_int("self")
        assert mock_set.call_args[0][1] == 42

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_unserializable_result_skips_cache(self, mock_get, mock_set):
        mock_get.return_value = None

        @cached(ttl=30, prefix="t")
        def get_object(self_arg):
            return object()

        result = get_object("self")
        assert result is not None
        mock_set.assert_not_called()

    def test_exposes_cache_prefix_attribute(self):
        @cached(ttl=99, prefix="my_prefix")
        def fn():
            pass

        assert fn._cache_prefix == "my_prefix"

    def test_exposes_cache_ttl_attribute(self):
        @cached(ttl=99, prefix="my_prefix")
        def fn():
            pass

        assert fn._cache_ttl == 99

    def test_preserves_function_metadata(self):
        @cached(ttl=60, prefix="p")
        def my_function_with_docs(self_arg, x: int) -> dict:
            """Return something useful."""
            return {}

        assert my_function_with_docs.__name__ == "my_function_with_docs"
        assert my_function_with_docs.__doc__ == "Return something useful."

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_default_prefix_and_ttl(self, mock_get, mock_set):
        """When no args given to @cached(), defaults are used."""
        mock_get.return_value = None

        @cached()
        def default_fn(self_arg):
            return {"ok": True}

        assert default_fn._cache_prefix == "datapulse"
        assert default_fn._cache_ttl == 300

    @patch("datapulse.cache_decorator.cache_set")
    @patch("datapulse.cache_decorator.cache_get")
    def test_cache_key_uses_function_name(self, mock_get, mock_set):
        """The cache key incorporates the actual function name."""
        mock_get.return_value = None

        @cached(ttl=60, prefix="test")
        def specific_method_name(self_arg):
            return {}

        specific_method_name("self")

        cache_key = mock_get.call_args[0][0]
        assert "specific_method_name" in cache_key
        assert cache_key.startswith("test:")
