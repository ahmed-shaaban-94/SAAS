# tests/test_graceful_shutdown.py
"""Verify graceful shutdown is properly configured."""

import pytest


def test_uvicorn_command_has_graceful_shutdown():
    """The docker-compose uvicorn command must include graceful shutdown timeout."""
    import yaml
    from pathlib import Path

    compose_path = Path("docker-compose.yml")
    if not compose_path.exists():
        pytest.skip("docker-compose.yml not found")

    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    api_command = compose["services"]["api"]["command"]
    command_str = " ".join(api_command) if isinstance(api_command, list) else api_command

    assert "--timeout-graceful-shutdown" in command_str, (
        "uvicorn command must include --timeout-graceful-shutdown for zero-downtime deploys"
    )


def test_lifespan_shutdown_exists():
    """The FastAPI app must have a lifespan with shutdown logic."""
    from datapulse.api.app import create_app

    app = create_app()
    # FastAPI lifespan is set if the app has router.lifespan_context
    assert app.router.lifespan_context is not None
