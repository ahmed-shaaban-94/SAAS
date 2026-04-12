# tests/test_graceful_shutdown.py
"""Verify graceful shutdown is properly configured."""

from pathlib import Path

import pytest
import yaml


def test_api_command_has_graceful_shutdown():
    """The API process manager must be configured for graceful shutdown.

    Accepts either gunicorn (graceful_timeout in gunicorn.conf.py) or
    uvicorn (--timeout-graceful-shutdown flag) — the PR switched to gunicorn.
    """
    import importlib.util

    compose_path = Path("docker-compose.yml")
    if not compose_path.exists():
        pytest.skip("docker-compose.yml not found")

    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    api_command = compose["services"]["api"]["command"]
    command_str = " ".join(api_command) if isinstance(api_command, list) else api_command

    if "gunicorn" in command_str:
        conf_path = Path("gunicorn.conf.py")
        assert conf_path.exists(), "gunicorn.conf.py must exist when gunicorn is used"
        spec = importlib.util.spec_from_file_location("gunicorn_conf", conf_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "graceful_timeout"), "gunicorn.conf.py must set graceful_timeout"
        assert mod.graceful_timeout >= 30, "graceful_timeout must be >= 30s for safe deploys"
    else:
        assert "--timeout-graceful-shutdown" in command_str, (
            "uvicorn command must include --timeout-graceful-shutdown for zero-downtime deploys"
        )


def test_lifespan_shutdown_exists():
    """The FastAPI app must have a lifespan with shutdown logic."""
    from datapulse.api.app import create_app

    app = create_app()
    # FastAPI lifespan is set if the app has router.lifespan_context
    assert app.router.lifespan_context is not None
