"""Tests for pipeline retry logic."""

from __future__ import annotations

import pytest

from datapulse.pipeline.retry import RetryExhaustedError, with_retry


class TestWithRetry:
    """Tests for the @with_retry decorator."""

    def test_succeeds_on_first_attempt(self):
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def always_works():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = always_works()
        assert result == "ok"
        assert call_count == 1

    def test_retries_on_transient_error_then_succeeds(self):
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def fails_once():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("connection reset")
            return "recovered"

        result = fails_once()
        assert result == "recovered"
        assert call_count == 2

    def test_exhausts_retries_raises_error(self):
        @with_retry(max_attempts=2, base_delay=0.01)
        def always_fails():
            raise ConnectionError("always down")

        with pytest.raises(RetryExhaustedError) as exc_info:
            always_fails()

        assert exc_info.value.attempts == 2
        assert "always down" in str(exc_info.value.last_error)
        assert exc_info.value.stage == "always_fails"

    def test_non_retryable_exception_raises_immediately(self):
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not transient")

        with pytest.raises(ValueError, match="not transient"):
            raises_value_error()

        assert call_count == 1  # no retries

    def test_custom_retryable_exceptions(self):
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01, retryable=(ValueError,))
        def fails_with_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("custom retryable")

        with pytest.raises(RetryExhaustedError):
            fails_with_value_error()

        assert call_count == 3

    def test_backoff_factor(self):
        """Verify the decorator calls with increasing delays (tested via attempt count)."""
        call_count = 0

        @with_retry(max_attempts=4, base_delay=0.01, backoff_factor=2.0)
        def always_timeout():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("timeout")

        with pytest.raises(RetryExhaustedError):
            always_timeout()

        assert call_count == 4

    def test_preserves_function_name(self):
        @with_retry()
        def my_stage_function():
            pass

        assert my_stage_function.__name__ == "my_stage_function"

    def test_os_error_is_retryable(self):
        call_count = 0

        @with_retry(max_attempts=2, base_delay=0.01)
        def network_issue():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("network unreachable")
            return "ok"

        result = network_issue()
        assert result == "ok"
        assert call_count == 2


class TestRetryExhaustedError:
    def test_error_message_format(self):
        original = ConnectionError("lost connection")
        err = RetryExhaustedError("bronze", 3, original)
        assert "bronze" in str(err)
        assert "3 attempts" in str(err)
        assert "lost connection" in str(err)

    def test_error_attributes(self):
        original = TimeoutError("timed out")
        err = RetryExhaustedError("dbt_staging", 5, original)
        assert err.stage == "dbt_staging"
        assert err.attempts == 5
        assert err.last_error is original
