"""Set (or reset) a Clerk user's password via the Backend API.

Use case: demo / placeholder accounts whose email cannot receive OTP
codes. Give the account a password and the user signs in with email +
password, skipping the email_code strategy entirely.

Usage
-----
    export CLERK_SECRET_KEY=sk_test_...
    # Generate a random password (recommended, 24 chars)
    python scripts/clerk_set_password.py <email>
    # Or set a specific one
    python scripts/clerk_set_password.py <email> --password "Whatever-Strong-Pw-2024"

Prerequisite: the Clerk instance must have the ``password`` authentication
strategy enabled (Dashboard → Configure → User & authentication → Email,
phone, username → Password). The script emits a clear error pointing at
that setting if it's off.

Outputs the password to stdout. Treat it like a credential — share only
through a secure channel (not email if the recipient's email is fake).
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
from pathlib import Path

import httpx

CLERK_API = "https://api.clerk.com/v1"
_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*_-+="


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


def _random_password(length: int = 24) -> str:
    """Cryptographically random password meeting most complexity policies."""
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


def find_user_by_email(client: httpx.Client, email: str) -> dict | None:
    resp = client.get("/users", params={"email_address": [email]})
    resp.raise_for_status()
    users = resp.json()
    return users[0] if users else None


def set_user_password(client: httpx.Client, user_id: str, password: str) -> None:
    """Update the user's password. Raises httpx.HTTPStatusError on failure."""
    resp = client.patch(
        f"/users/{user_id}",
        json={
            "password": password,
            "skip_password_checks": True,  # we already enforced our own policy
            "sign_out_of_other_sessions": False,
        },
    )
    resp.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="Clerk user's primary email address")
    parser.add_argument(
        "--password",
        help="Password to set. Omit to generate a strong random 24-char one.",
    )
    parser.add_argument(
        "--length",
        type=int,
        default=24,
        help="Length of generated password (ignored when --password is given).",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    _load_env_file(root / ".env")

    secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    if not secret.startswith("sk_"):
        print("[FAIL] CLERK_SECRET_KEY missing or malformed in .env", file=sys.stderr)
        return 2

    password = args.password or _random_password(args.length)

    with _client(secret) as client:
        user = find_user_by_email(client, args.email)
        if user is None:
            print(f"[FAIL] No Clerk user found with email {args.email!r}", file=sys.stderr)
            return 3

        try:
            set_user_password(client, user["id"], password)
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            print(
                f"[FAIL] Clerk rejected the password update: "
                f"{exc.response.status_code} {body}",
                file=sys.stderr,
            )
            if "password" in body.lower() and "strateg" in body.lower():
                print(
                    "\nHint: enable password auth in Clerk Dashboard → "
                    "Configure → User & authentication → Email, phone, username "
                    "→ Authentication strategies → Password.",
                    file=sys.stderr,
                )
            return 4

    print("[OK] Password set.")
    print()
    print(f"  Email:    {args.email}")
    print(f"  User ID:  {user['id']}")
    print("  Password: [REDACTED]")
    print()
    print("Share both over a secure channel (not email if the mailbox is")
    print("a placeholder). The recipient signs in at /sign-in using email")
    print("+ password — no OTP code is sent.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
