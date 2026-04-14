"""SSH tunnel for brain DB access from a Windows dev machine.

When BRAIN_SSH_HOST is set, the brain tools automatically tunnel the
droplet's PostgreSQL through SSH — no port exposure on the server needed.

Env vars (set in .env or MCP server env):
    BRAIN_SSH_HOST          Droplet IP (e.g. 164.92.243.3)
    BRAIN_SSH_USER          SSH user (default: root)
    BRAIN_SSH_KEY           Path to SSH private key (default: ~/.ssh/id_ed25519)
    BRAIN_SSH_REMOTE_PORT   Remote postgres port (default: 5432)
    BRAIN_DB_USER           Postgres user (default: datapulse)
    BRAIN_DB_PASSWORD       Postgres password
    BRAIN_DB_NAME           Postgres database name (default: datapulse)

The tunnel is a process-level singleton — created on first use, reused for
all subsequent connections, and terminated cleanly on process exit.
"""

from __future__ import annotations

import atexit
import os
import socket
import subprocess
import time

_tunnel_proc: subprocess.Popen | None = None
_tunnel_port: int | None = None


def _free_port() -> int:
    """Find a free local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    """Wait until a local port accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def ensure_tunnel() -> int | None:
    """Start an SSH tunnel if BRAIN_SSH_HOST is configured.

    Returns the local forwarded port number, or None if SSH is not configured.
    Safe to call multiple times — the tunnel is created once and reused.

    Raises RuntimeError if the tunnel fails to open within the timeout.
    """
    global _tunnel_proc, _tunnel_port

    ssh_host = os.environ.get("BRAIN_SSH_HOST", "").strip()
    if not ssh_host:
        return None

    # Reuse if the tunnel process is still alive
    if _tunnel_proc is not None and _tunnel_proc.poll() is None:
        return _tunnel_port

    ssh_user = os.environ.get("BRAIN_SSH_USER", "root")
    ssh_key = os.path.expanduser(
        os.environ.get("BRAIN_SSH_KEY", "~/.ssh/id_ed25519")
    )
    remote_port = int(os.environ.get("BRAIN_SSH_REMOTE_PORT", "5432"))
    local_port = _free_port()

    _tunnel_proc = subprocess.Popen(
        [
            "ssh",
            "-i", ssh_key,
            "-L", f"{local_port}:localhost:{remote_port}",
            "-N",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "BatchMode=yes",
            f"{ssh_user}@{ssh_host}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    atexit.register(_tunnel_proc.terminate)

    if not _wait_for_port(local_port):
        _tunnel_proc.terminate()
        _tunnel_proc = None
        raise RuntimeError(
            f"SSH tunnel to {ssh_host}:{remote_port} did not open on "
            f"local port {local_port} within 15 seconds. "
            f"Check BRAIN_SSH_HOST, BRAIN_SSH_KEY, and SSH key auth."
        )

    _tunnel_port = local_port
    return local_port


def tunnel_database_url() -> str | None:
    """Build a DATABASE_URL via SSH tunnel.

    Returns None if BRAIN_SSH_HOST is not set or BRAIN_DB_PASSWORD is missing.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    port = ensure_tunnel()
    if port is None:
        return None

    user = os.environ.get("BRAIN_DB_USER", "datapulse")
    password = os.environ.get("BRAIN_DB_PASSWORD", "")
    db_name = os.environ.get("BRAIN_DB_NAME", "datapulse")

    if not password:
        return None  # Can't connect without credentials

    # URL-encode the password to handle special characters
    from urllib.parse import quote_plus
    return f"postgresql://{user}:{quote_plus(password)}@127.0.0.1:{port}/{db_name}"
