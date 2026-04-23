#!/usr/bin/env python3
"""CI guard: detect unsafe tenant-session patterns in Python source.

Two checks:
  1. f-string interpolation in SET LOCAL app.tenant_id — potential SQL injection.
     Correct form: session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})

  2. Raw get_session_factory()() calls outside the allowed infrastructure files.
     Application code (routes, services, repos, tasks, scheduler) must use
     tenant_session() from datapulse.core.db_session or go through FastAPI Depends.

Allowed infrastructure files (may still call get_session_factory directly):
  - src/datapulse/core/auth.py
  - src/datapulse/core/db_session.py
  - src/datapulse/core/db.py
  - src/datapulse/api/deps.py

Usage:
    python scripts/check_session_safety.py          # scans src/
    python scripts/check_session_safety.py src/     # explicit path
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FSTRING_PATTERN = re.compile(
    r"""SET\s+LOCAL\s+app\.tenant_id\s*=\s*['"]\s*\{""",
    re.IGNORECASE,
)

RAW_FACTORY_PATTERN = re.compile(r"get_session_factory\(\)\(\)")

ALLOWED_RAW_FACTORY_FILES = {
    "src/datapulse/core/auth.py",
    "src/datapulse/core/db_session.py",
    "src/datapulse/core/db.py",
    "src/datapulse/api/deps.py",
}

_KNOWN_FILE = Path(__file__).parent / ".known-session-violations"


def _load_known_violations() -> set[str]:
    """Return set of 'rel/path.py:lineno' strings that are grandfathered."""
    if not _KNOWN_FILE.exists():
        return set()
    known: set[str] = set()
    for line in _KNOWN_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            known.add(line)
    return known

ROOT = Path(__file__).parent.parent


def check_file(path: Path, known: set[str]) -> list[str]:
    errors: list[str] = []
    rel = str(path.relative_to(ROOT))
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return errors

    for lineno, line in enumerate(source.splitlines(), 1):
        if FSTRING_PATTERN.search(line):
            errors.append(
                f"{rel}:{lineno}: f-string in SET LOCAL app.tenant_id — "
                "use parameterised query: "
                'execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})'
            )
        if (
            RAW_FACTORY_PATTERN.search(line)
            and rel not in ALLOWED_RAW_FACTORY_FILES
            and f"{rel}:{lineno}" not in known
        ):
            errors.append(
                f"{rel}:{lineno}: raw get_session_factory()() call outside "
                "infrastructure layer — use tenant_session() from "
                "datapulse.core.db_session instead"
            )
    return errors


def main() -> int:
    known = _load_known_violations()
    roots = [Path(a) for a in sys.argv[1:]] or [ROOT / "src"]
    all_errors: list[str] = []
    for root in roots:
        for py in sorted(root.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            all_errors.extend(check_file(py, known))

    if all_errors:
        print("Session safety violations found:\n")
        for err in all_errors:
            print(f"  {err}")
        print(f"\n{len(all_errors)} violation(s). Fix before merging.")
        return 1

    print(f"Session safety: OK (scanned {sum(1 for r in roots for _ in r.rglob('*.py'))} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
