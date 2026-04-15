"""SSH tunnel for brain DB access from a Windows dev machine.

When BRAIN_SSH_HOST is set, the brain tools automatically tunnel the
droplet's PostgreSQL through SSH — no port exposure on the server needed.

Strategy: Docker prod stacks bind postgres to 127.0.0.1 only (or not at all).
We resolve the container's internal Docker network IP via `docker inspect`,
then tunnel directly to *that* IP — bypassing host port bindings entirely.

Env vars (set in .env or .mcp.json):
    BRAIN_SSH_HOST          Droplet IP or hostname  (e.g. 164.92.243.3)
    BRAIN_SSH_USER          SSH user                (default: root)
    BRAIN_SSH_KEY           Path to SSH private key (default: ~/.ssh/id_ed25519)
    BRAIN_DB_CONTAINER      Postgres container name (default: datapulse-db)
    BRAIN_DB_USER           Postgres user           (default: datapulse)
    BRAIN_DB_PASSWORD       Postgres password
    BRAIN_DB_NAME           Postgres database name  (default: datapulse)

The tunnel is a process-level singleton — created on first use, reused for
all subsequent connections in the same process, terminated cleanly on exit.
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
    """Bind to port 0 to let the OS pick a free port, then release it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    """Poll until a TCP connection to 127.0.0.1:port succeeds or times out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _ssh_base_args(ssh_user: str, ssh_host: str, ssh_key: str) -> list[str]:
    """Return common SSH args shared by the inspect and tunnel invocations."""
    return [
        "ssh",
        "-i",
        ssh_key,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        f"{ssh_user}@{ssh_host}",
    ]


def _resolve_container_ip(
    ssh_user: str,
    ssh_host: str,
    ssh_key: str,
    container: str,
) -> str:
    """Return the container's first Docker network IP via docker inspect over SSH.

    Falls back to "localhost" if the container is not found or the command fails
    (covers local-dev scenarios where postgres IS on localhost:5432).
    """
    try:
        result = subprocess.run(
            _ssh_base_args(ssh_user, ssh_host, ssh_key)
            + [
                f"docker inspect {container} "
                f"--format '{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}'"
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        ip = result.stdout.strip().strip("'\"")
        if ip:
            return ip
    except Exception:
        pass
    return "localhost"


def ensure_tunnel() -> int | None:
    """Start an SSH tunnel to the droplet's postgres container if BRAIN_SSH_HOST is set.

    Returns the local forwarded port, or None if SSH is not configured.
    Calling this multiple times is safe — the tunnel is reused.

    Raises RuntimeError if the tunnel cannot be established within 15 s.
    """
    global _tunnel_proc, _tunnel_port

    ssh_host = os.environ.get("BRAIN_SSH_HOST", "").strip()
    if not ssh_host:
        return None

    # Reuse existing tunnel if the process is still alive
    if _tunnel_proc is not None and _tunnel_proc.poll() is None:
        return _tunnel_port

    ssh_user = os.environ.get("BRAIN_SSH_USER", "root")
    ssh_key = os.path.expanduser(os.environ.get("BRAIN_SSH_KEY", "~/.ssh/id_ed25519"))
    container = os.environ.get("BRAIN_DB_CONTAINER", "datapulse-db")
    remote_port = 5432
    local_port = _free_port()

    # Resolve the container's internal Docker IP so we bypass host port bindings.
    # Production stacks often reset postgres ports to [] — the container is only
    # reachable on the Docker bridge network, not on the host's localhost.
    container_ip = _resolve_container_ip(ssh_user, ssh_host, ssh_key, container)

    _tunnel_proc = subprocess.Popen(
        _ssh_base_args(ssh_user, ssh_host, ssh_key)[:-1]  # drop the host arg
        + [
            "-L",
            f"{local_port}:{container_ip}:{remote_port}",
            "-N",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
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
            f"SSH tunnel to {container_ip}:{remote_port} via {ssh_host} "
            f"did not open on local port {local_port} within 15 s. "
            f"Check BRAIN_SSH_HOST, BRAIN_SSH_KEY, and SSH key auth."
        )

    _tunnel_port = local_port
    return local_port


def tunnel_database_url() -> str | None:
    """Return a psycopg2-compatible URL that connects through the SSH tunnel.

    Returns None if BRAIN_SSH_HOST is not set or BRAIN_DB_PASSWORD is missing
    (callers fall back to DATABASE_URL / BRAIN_DATABASE_URL).
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
        return None  # Fall through to direct URL path

    from urllib.parse import quote_plus

    return f"postgresql://{user}:{quote_plus(password)}@127.0.0.1:{port}/{db_name}"
