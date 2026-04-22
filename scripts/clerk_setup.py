"""One-shot Clerk admin setup for the DataPulse migration.

Creates (or updates) the ``datapulse`` JWT template and seeds
``public_metadata.tenant_id`` + ``public_metadata.roles`` on every existing
Clerk user so the backend RLS layer keeps working unchanged.

Idempotent: safe to re-run. Reads secrets from the environment — never
hardcode the key here.

Usage
-----
    export CLERK_SECRET_KEY=sk_test_...
    python scripts/clerk_setup.py [--tenant-id 1] [--role owner]

Why a script instead of MCP? The Clerk MCP server requires a Claude Code
session restart after registration, which breaks our working session.
This script uses Clerk's Backend REST API with the same secret so
we can make progress now; the MCP remains available for future sessions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

CLERK_API = "https://api.clerk.com/v1"

# Template name defaults to "datapulse" but honors CLERK_JWT_TEMPLATE so a
# custom name in .env + script + backend config stay in lockstep.
TEMPLATE_NAME = os.environ.get("CLERK_JWT_TEMPLATE", "datapulse")

# Claims shape: keeps namespaced + flat keys so core/auth.py reads them
# identically to Auth0 tokens (no claim-extraction changes required).
TEMPLATE_CLAIMS: dict[str, Any] = {
    "tenant_id": "{{user.public_metadata.tenant_id}}",
    "https://datapulse.tech/tenant_id": "{{user.public_metadata.tenant_id}}",
    "roles": "{{user.public_metadata.roles}}",
    "https://datapulse.tech/roles": "{{user.public_metadata.roles}}",
    "email": "{{user.primary_email_address}}",
    "preferred_username": "{{user.username}}",
}


def _load_env_file(path: Path) -> None:
    """Poor-man's python-dotenv for one-shot scripts."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _client(secret: str) -> httpx.Client:
    return httpx.Client(
        base_url=CLERK_API,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
        },
        timeout=15.0,
    )


def _find_template(client: httpx.Client, name: str) -> dict[str, Any] | None:
    resp = client.get("/jwt_templates")
    resp.raise_for_status()
    for tpl in resp.json():
        if tpl.get("name") == name:
            return tpl
    return None


def ensure_jwt_template(client: httpx.Client) -> dict[str, Any]:
    payload = {
        "name": TEMPLATE_NAME,
        "claims": TEMPLATE_CLAIMS,
        "signing_algorithm": "RS256",
        "lifetime": 3600,
        "allowed_clock_skew": 5,
    }
    existing = _find_template(client, TEMPLATE_NAME)
    if existing is None:
        resp = client.post("/jwt_templates", json=payload)
        resp.raise_for_status()
        print(f"[OK] Created JWT template '{TEMPLATE_NAME}'")
        return resp.json()

    resp = client.patch(f"/jwt_templates/{existing['id']}", json=payload)
    resp.raise_for_status()
    print(f"[OK] Updated JWT template '{TEMPLATE_NAME}' ({existing['id']})")
    return resp.json()


def list_users(client: httpx.Client) -> list[dict[str, Any]]:
    users: list[dict[str, Any]] = []
    offset = 0
    limit = 100
    while True:
        resp = client.get("/users", params={"offset": offset, "limit": limit})
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        users.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return users


def seed_user_metadata(
    client: httpx.Client,
    user: dict[str, Any],
    default_tenant_id: str,
    default_role: str,
) -> bool:
    """Set public_metadata.tenant_id + roles if missing. Returns True if updated."""
    public = user.get("public_metadata") or {}
    current_tid = public.get("tenant_id")
    current_roles = public.get("roles")

    needs_update = not current_tid or not current_roles
    if not needs_update:
        return False

    merged = {
        **public,
        "tenant_id": current_tid or default_tenant_id,
        "roles": current_roles or [default_role],
    }
    resp = client.patch(
        f"/users/{user['id']}/metadata",
        json={"public_metadata": merged},
    )
    resp.raise_for_status()
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", default="1", help="Default tenant_id for users lacking one")
    parser.add_argument("--role", default="owner", help="Default role for users lacking one")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    _load_env_file(root / ".env")

    # Re-evaluate TEMPLATE_NAME after .env is loaded (env var might have been
    # set there rather than in the parent shell).
    global TEMPLATE_NAME
    TEMPLATE_NAME = os.environ.get("CLERK_JWT_TEMPLATE", "datapulse")

    secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    if not secret.startswith("sk_"):
        print("[FAIL] CLERK_SECRET_KEY missing or malformed in .env", file=sys.stderr)
        return 2

    with _client(secret) as client:
        try:
            client.get("/jwt_templates").raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(
                f"[FAIL] Clerk API auth check failed: {exc.response.status_code} "
                f"{exc.response.text}",
                file=sys.stderr,
            )
            return 3

        if args.dry_run:
            print("[DRY-RUN] Skipping template + metadata writes.")
            users = list_users(client)
            print(f"[INFO] Found {len(users)} users.")
            return 0

        tpl = ensure_jwt_template(client)
        print(f"       claims: {json.dumps(tpl.get('claims'), indent=2)}")

        users = list_users(client)
        print(f"[OK] Found {len(users)} users in Clerk.")
        updated = 0
        for u in users:
            if seed_user_metadata(client, u, args.tenant_id, args.role):
                updated += 1
                email = ""
                for addr in u.get("email_addresses", []):
                    if addr.get("id") == u.get("primary_email_address_id"):
                        email = addr.get("email_address", "")
                        break
                print(f"       seeded {u['id']} ({email or 'no-email'})")

        if updated == 0:
            print("[OK] All users already had tenant_id + roles metadata.")
        else:
            print(f"[OK] Seeded metadata on {updated}/{len(users)} users.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
