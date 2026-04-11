"""Tests for the API stabilization changes.

Covers:
- Streaming upload (2.1)
- JWT retry reduction (2.2)
- AI client timeout reduction (2.3)
- Prometheus metrics module (3.1)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 2.1 — Streaming upload rejects oversized files without full buffering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file_mid_stream():
    """Streaming upload raises 413 before reading the entire file."""
    from fastapi import HTTPException

    from datapulse.api.routes.upload import upload_files

    # Simulate a file that yields 2MB chunks — 60 chunks = 120MB (over 100MB limit)
    chunk = b"x" * (2 * 1024 * 1024)
    call_count = 0

    async def _mock_read(size=-1):
        nonlocal call_count
        call_count += 1
        if call_count > 60:
            return b""
        return chunk

    mock_file = MagicMock()
    mock_file.filename = "big.csv"
    mock_file.size = None  # no declared size — triggers stream-based check only
    mock_file.read = _mock_read

    mock_request = MagicMock()
    mock_service = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await upload_files(
            request=mock_request,
            files=[mock_file],
            service=mock_service,
        )

    assert exc_info.value.status_code == 413
    # Should NOT have read all 60 chunks — should have stopped around 50 (100MB / 2MB)
    assert call_count <= 52


@pytest.mark.asyncio
async def test_upload_accepts_small_file():
    """Streaming upload accepts files under the limit."""
    from datapulse.api.routes.upload import upload_files

    content = b"name,value\nfoo,1\n"
    calls = 0

    async def _mock_read(size=-1):
        nonlocal calls
        calls += 1
        if calls == 1:
            return content
        return b""

    mock_file = MagicMock()
    mock_file.filename = "small.csv"
    mock_file.size = None  # no declared size — triggers stream-based check only
    mock_file.read = _mock_read

    mock_request = MagicMock()
    mock_service = MagicMock()
    mock_service.save_temp_file.return_value = MagicMock()

    result = await upload_files(
        request=mock_request,
        files=[mock_file],
        service=mock_service,
    )

    assert len(result) == 1
    mock_service.save_temp_file.assert_called_once_with("small.csv", content)


# ---------------------------------------------------------------------------
# 2.2 — JWT retry delays reduced
# ---------------------------------------------------------------------------


def test_jwt_retry_delays_reduced():
    """JWKS retry delays are shorter than the original (1, 2, 4) pattern."""
    from datapulse.api.jwt import _JWKS_RETRY_DELAYS

    assert sum(_JWKS_RETRY_DELAYS) < 7.0  # was 7.0 (1+2+4)
    assert max(_JWKS_RETRY_DELAYS) <= 2.0  # was 4.0


# ---------------------------------------------------------------------------
# 2.3 — AI client timeout reduced
# ---------------------------------------------------------------------------


def test_ai_client_timeout_reduced():
    """OpenRouter timeout is 30s, not 60s."""
    import datapulse.ai_light.client as ai_mod

    settings = MagicMock()
    settings.openrouter_api_key = "test-key"
    settings.openrouter_model = "test/model"
    client = ai_mod.OpenRouterClient(settings)

    # Verify by inspecting the code — the timeout is embedded in the method
    # We can test by checking the httpx.post call
    with (
        patch("datapulse.ai_light.client.httpx.post") as mock_post,
        patch("datapulse.ai_light.client.time.sleep"),
    ):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "usage": {"total_tokens": 10},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client.chat("system", "user")

        # Verify timeout is 30, not 60
        _, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 30


# ---------------------------------------------------------------------------
# 3.1 — Prometheus metrics module
# ---------------------------------------------------------------------------


def test_metrics_module_available():
    """Custom Prometheus metrics are importable."""
    from datapulse import metrics

    # Should be available since prometheus_client is a dependency
    assert metrics.METRICS_AVAILABLE is True
    # Verify all expected metrics exist
    assert hasattr(metrics, "db_pool_checked_out")
    assert hasattr(metrics, "pipeline_duration_seconds")
    assert hasattr(metrics, "pipeline_runs_total")
    assert hasattr(metrics, "pipeline_stale_detected")
    assert hasattr(metrics, "scheduler_is_leader")
    assert hasattr(metrics, "scheduler_jobs_executed")


def test_metrics_can_increment():
    """Verify metrics support the API calls used in scheduler.py."""
    from datapulse import metrics

    # These calls must not raise — they're called in scheduler.py
    metrics.scheduler_is_leader.set(1)
    metrics.scheduler_is_leader.set(0)
    metrics.scheduler_jobs_executed.labels(job="test").inc()
    metrics.pipeline_runs_total.labels(status="success").inc()
    metrics.pipeline_duration_seconds.observe(5.0)
    metrics.pipeline_stale_detected.inc()


# ---------------------------------------------------------------------------
# 1.2 — Pool size defaults
# ---------------------------------------------------------------------------


def test_pool_defaults_fit_multi_worker():
    """Default pool settings support 4 workers within PG max_connections=100."""
    with patch.dict("os.environ", {"DATABASE_URL": "postgresql://x@localhost/test"}):
        from datapulse.core.config import Settings

        settings = Settings(database_url="postgresql://x@localhost/test")  # type: ignore[call-arg]
        per_worker = settings.db_pool_size + settings.db_pool_max_overflow
        total_4_workers = per_worker * 4 + 5  # +5 admin headroom
        assert total_4_workers <= 100, f"4 workers use {total_4_workers} connections (max 100)"
