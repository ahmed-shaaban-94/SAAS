"""Egyptian mobile number normaliser for POS customer lookup (#624).

Cashiers type phones in three shapes:

* ``01XXXXXXXXX``    — 11-digit local with leading 0
* ``201XXXXXXXXX``   — 12-digit international without ``+``
* ``+201XXXXXXXXX``  — 12-digit international E.164

We normalise to the E.164 canonical (``+201XXXXXXXXX``) on both the write
path (so the DB holds one shape) and the read path (so the terminal can send
any of the three to ``/customers/by-phone/{phone}`` and still hit the row).

Landline / international numbers are intentionally rejected — the POS lookup
is purpose-built for mobile-driven loyalty + churn, and accepting landlines
would silently let the UNIQUE index on (tenant_id, phone_e164) collide with
"legitimate" rows coming from other normalisation paths.
"""

from __future__ import annotations

import re

_E164_RE = re.compile(r"^\+20[0-9]{10}$")


def normalize_egyptian_phone(raw: str | None) -> str | None:
    """Return the E.164 canonical form of ``raw`` or ``None`` on invalid input.

    Accepts three input shapes:

    * ``01XXXXXXXXX``   -> ``+201XXXXXXXXX``
    * ``201XXXXXXXXX``  -> ``+201XXXXXXXXX``
    * ``+201XXXXXXXXX`` -> ``+201XXXXXXXXX`` (already canonical)

    Whitespace, dashes, dots, and parentheses are stripped before matching;
    ``None`` / empty / unknown shapes return ``None`` so callers can surface
    a 400 or a user-facing "invalid format" without raising.
    """
    if raw is None:
        return None
    cleaned = re.sub(r"[\s\-().]", "", raw)
    if not cleaned:
        return None
    if cleaned.startswith("+"):
        candidate = cleaned
    elif cleaned.startswith("00"):
        candidate = "+" + cleaned[2:]
    elif cleaned.startswith("20"):
        candidate = "+" + cleaned
    elif cleaned.startswith("0"):
        candidate = "+2" + cleaned
    else:
        return None

    if _E164_RE.match(candidate):
        return candidate
    return None
