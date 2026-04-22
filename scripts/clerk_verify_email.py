"""Mark a Clerk user's email address as verified (admin override).

Use case: demo / placeholder accounts where the email is fake and
cannot receive the standard verification code. Flipping the address
``verification.status`` to ``verified`` via the admin API lets the
user sign in immediately without going through email_code.

Usage
-----
    export CLERK_SECRET_KEY=sk_test_...
    python scripts/clerk_verify_email.py <email>
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

CLERK_API = "https://api.clerk.com/v1"


def _load_env_file(path: Path) -> None:
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


def find_user_by_email(client: httpx.Client, email: str) -> dict | None:
    resp = client.get("/users", params={"email_address": [email]})
    resp.raise_for_status()
    users = resp.json()
    return users[0] if users else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="Email to mark as verified")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    _load_env_file(root / ".env")

    secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    if not secret.startswith("sk_"):
        print("[FAIL] CLERK_SECRET_KEY missing in .env", file=sys.stderr)
        return 2

    with _client(secret) as client:
        user = find_user_by_email(client, args.email)
        if user is None:
            print(f"[FAIL] User {args.email!r} not found", file=sys.stderr)
            return 3

        # Find the matching email_address object
        target = None
        for addr in user.get("email_addresses", []):
            if addr.get("email_address") == args.email:
                target = addr
                break
        if target is None:
            print(f"[FAIL] Email {args.email!r} not attached to user {user['id']}", file=sys.stderr)
            return 4

        if target.get("verification", {}).get("status") == "verified":
            print(f"[OK] Already verified (user={user['id']}, email={target['id']}).")
            return 0

        resp = client.patch(
            f"/users/{user['id']}/email_addresses/{target['id']}",
            json={"verified": True},
        )
        if resp.status_code >= 400:
            print(
                f"[FAIL] Clerk rejected the verify update: "
                f"{resp.status_code} {resp.text}",
                file=sys.stderr,
            )
            return 5

    print(f"[OK] Marked {args.email!r} as verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
