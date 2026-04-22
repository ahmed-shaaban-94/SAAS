"""Generate a one-click Clerk sign-in URL — no email code, no password.

Use case: share the DataPulse dashboard with a supervisor whose email
address is a placeholder / cannot receive OTP codes. The sign-in token
carries identity for a single session; once they click the URL they are
signed in as that user and redirected to the dashboard.

Clerk documents this under **Backend API → Sign-in Tokens**:
https://clerk.com/docs/reference/backend-api/tag/Sign-in-Tokens

Usage
-----
    export CLERK_SECRET_KEY=sk_test_...
    python scripts/clerk_create_sign_in_link.py <email> [--expires-days 30] [--redirect /dashboard]

The printed URL is single-use (per Clerk's default). If the supervisor
needs to log in again later, re-run the script to mint a fresh one.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

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


def create_sign_in_token(
    client: httpx.Client,
    user_id: str,
    expires_in_seconds: int,
) -> dict:
    resp = client.post(
        "/sign_in_tokens",
        json={"user_id": user_id, "expires_in_seconds": expires_in_seconds},
    )
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="Clerk user's primary email address")
    parser.add_argument(
        "--expires-days",
        type=int,
        default=30,
        help="How long the sign-in link stays usable (default 30 days).",
    )
    parser.add_argument(
        "--redirect",
        default="/dashboard",
        help="Where Clerk sends the user after sign-in (default /dashboard).",
    )
    parser.add_argument(
        "--app-url",
        default=os.environ.get("APP_URL", "http://localhost:3000"),
        help="Base URL of the running DataPulse frontend.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    _load_env_file(root / ".env")

    secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    if not secret.startswith("sk_"):
        print("[FAIL] CLERK_SECRET_KEY missing or malformed in .env", file=sys.stderr)
        return 2

    with _client(secret) as client:
        user = find_user_by_email(client, args.email)
        if user is None:
            print(f"[FAIL] No Clerk user found with email {args.email!r}", file=sys.stderr)
            return 3

        expires_in = max(60, args.expires_days * 24 * 3600)
        token = create_sign_in_token(client, user["id"], expires_in)

    # Clerk returns a hosted `url` that redeems the ticket automatically,
    # but using the app's own /sign-in?__clerk_ticket=… keeps the user
    # inside DataPulse's domain and honors our branded layout.
    qs = urlencode({"__clerk_ticket": token["token"], "redirect_url": args.redirect})
    direct_app_url = f"{args.app_url.rstrip('/')}/sign-in?{qs}"

    print("Sign-in link generated (single-use by default):")
    print()
    print(f"  {direct_app_url}")
    print()
    print(f"  Alt (Clerk-hosted):  {token.get('url', '<none returned>')}")
    print()
    print(f"User:    {user['id']}  ({args.email})")
    print(f"Expires: {args.expires_days} days")
    print(f"Token:   {token['id']} (status={token.get('status')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
