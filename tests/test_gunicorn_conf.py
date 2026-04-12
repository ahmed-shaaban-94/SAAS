"""Tests for gunicorn.conf.py — validates production config values."""

import importlib
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest


def _load_gunicorn_conf():
    """Import gunicorn.conf.py as a module from repo root."""
    conf_path = Path(__file__).parent.parent / "gunicorn.conf.py"
    spec = importlib.util.spec_from_file_location("gunicorn_conf", conf_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_gunicorn_conf_worker_class():
    """Worker class must be UvicornWorker for async support."""
    conf = _load_gunicorn_conf()
    assert conf.worker_class == "uvicorn.workers.UvicornWorker"


@pytest.mark.unit
def test_gunicorn_conf_timeout():
    """Timeout must kill stuck workers within 120s."""
    conf = _load_gunicorn_conf()
    assert conf.timeout == 120


@pytest.mark.unit
def test_gunicorn_conf_max_requests():
    """Max requests must be set to prevent memory leaks."""
    conf = _load_gunicorn_conf()
    assert conf.max_requests == 1000
    assert conf.max_requests_jitter == 100


@pytest.mark.unit
def test_gunicorn_conf_keepalive():
    """Keepalive must exceed nginx keepalive_timeout (65s)."""
    conf = _load_gunicorn_conf()
    assert conf.keepalive >= 70


@pytest.mark.unit
def test_gunicorn_conf_defaults_to_2_workers():
    """Default workers is 2 when WEB_CONCURRENCY is not set."""
    with patch.dict("os.environ", {}, clear=False):
        import os

        os.environ.pop("WEB_CONCURRENCY", None)
        conf = _load_gunicorn_conf()
        assert conf.workers == 2


@pytest.mark.unit
def test_gunicorn_conf_web_concurrency_override():
    """WEB_CONCURRENCY env var overrides worker count."""
    with patch.dict("os.environ", {"WEB_CONCURRENCY": "4"}):
        conf = _load_gunicorn_conf()
        assert conf.workers == 4
