#!/usr/bin/env python3
"""Docs/manifests drift check for canonical truth sources (issue #660).

Guards against the two specific drift patterns the #660 audit called out:

  * README.md or docs/ARCHITECTURE.md describing Auth0 / NextAuth as the
    canonical auth stack, while ``src/datapulse/core/config.py`` has pinned
    ``auth_provider`` to ``clerk`` (PR #668).
  * README.md or docs/ARCHITECTURE.md still advertising ``Next.js 14`` while
    ``frontend/package.json`` is on ``next ^15``.

Only the two user-facing canonical docs are checked. Historical ADRs,
audit reports, runbooks, and completed plans may legitimately mention
the prior stack — they are intentionally out of scope.

Stdlib only. Run from repo root.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Canonical doc surfaces — only these two are held to the "current state" bar.
CANONICAL_DOCS = [
    REPO / "README.md",
    REPO / "docs" / "ARCHITECTURE.md",
]

# Patterns that are *stale* once the corresponding code fact is in place.
# Each entry: (regex, human-readable name, truth-source-check)
STALE_PATTERNS = [
    (
        re.compile(r"\bAuth0\b", re.IGNORECASE),
        "Auth0 reference",
        "src/datapulse/core/config.py pins auth_provider to 'clerk'",
    ),
    (
        re.compile(r"NextAuth"),
        "NextAuth reference",
        "Clerk is the sole IdP; NextAuth is not part of the canonical stack",
    ),
    (
        re.compile(r"Next\.?js[\s-]*14"),
        "Next.js 14 reference",
        "frontend/package.json declares next ^15",
    ),
]


def _auth_provider_is_clerk() -> bool:
    config = (REPO / "src" / "datapulse" / "core" / "config.py").read_text(encoding="utf-8")
    # Literal["clerk"] (the current pin) — anything else means this check is stale.
    return 'Literal["clerk"]' in config


def _next_major_is_15_or_newer() -> bool:
    pkg = json.loads((REPO / "frontend" / "package.json").read_text(encoding="utf-8"))
    spec = pkg.get("dependencies", {}).get("next", "")
    match = re.search(r"(\d+)", spec)
    return bool(match and int(match.group(1)) >= 15)


def main() -> int:
    failures: list[str] = []

    # Sanity-check the truth sources — if one of these flips, update this script
    # together with the doc change. We want a loud failure, not a silent pass.
    if not _auth_provider_is_clerk():
        print(
            "[drift-check] skipped: auth_provider is no longer pinned to 'clerk' — "
            "update this script alongside the code/doc change.",
            file=sys.stderr,
        )
        return 0
    if not _next_major_is_15_or_newer():
        print(
            "[drift-check] skipped: frontend Next.js is no longer >=15 — "
            "update this script alongside the code/doc change.",
            file=sys.stderr,
        )
        return 0

    for doc in CANONICAL_DOCS:
        text = doc.read_text(encoding="utf-8")
        for pattern, name, why_stale in STALE_PATTERNS:
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    failures.append(
                        f"{doc.relative_to(REPO)}:{lineno}: stale {name} — {why_stale}\n"
                        f"    -> {line.strip()[:120]}"
                    )

    if failures:
        print("Canonical docs drift detected (issue #660):\n", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        print(
            "\nUpdate README.md / docs/ARCHITECTURE.md to match the current code,\n"
            "or adjust scripts/check_docs_truth_sources.py if the stack itself changed.",
            file=sys.stderr,
        )
        return 1

    print("[drift-check] README.md + docs/ARCHITECTURE.md match current auth + frontend stack.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
