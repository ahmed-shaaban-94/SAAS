"""CI guard: block raw tenant session setup outside ``datapulse.core.db``.

Issue #655. Application code must use the shared helpers in
``datapulse.core.db``:

- ``tenant_session_scope(...)``
- ``plain_session_scope(...)``
- ``apply_session_locals(...)``

This script fails when it finds either:
1. raw ``get_session_factory()()`` calls, or
2. ad hoc ``SET LOCAL app.tenant_id`` execution

outside the canonical helper module.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = REPO_ROOT / "src" / "datapulse"
ALLOWED_FILES = {
    (TARGET_DIR / "core" / "db.py").resolve(),
}

RAW_FACTORY_RE = re.compile(r"\bget_session_factory\(\)\(")
RAW_TENANT_SET_RE = re.compile(
    r"""\.\s*execute\(\s*(?:sa_)?text\(\s*f?["']SET\ LOCAL\ app\.tenant_id\b""",
)


def iter_violations() -> list[str]:
    violations: list[str] = []
    for py_file in sorted(TARGET_DIR.rglob("*.py")):
        if py_file.resolve() in ALLOWED_FILES:
            continue
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), start=1):
            if RAW_FACTORY_RE.search(line) or RAW_TENANT_SET_RE.search(line):
                rel = py_file.relative_to(REPO_ROOT).as_posix()
                violations.append(f"{rel}:{lineno}: {line.strip()}")
    return violations


def main() -> int:
    if not TARGET_DIR.is_dir():
        print(f"ERROR: target directory not found at {TARGET_DIR}", file=sys.stderr)
        return 1

    violations = iter_violations()
    if violations:
        print(
            "Session-scope usage check FAILED. Use "
            "`tenant_session_scope`, `plain_session_scope`, or "
            "`apply_session_locals` from `datapulse.core.db` instead.",
            file=sys.stderr,
        )
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    total_files = sum(1 for _ in TARGET_DIR.rglob("*.py"))
    print(
        f"Session-scope usage check PASSED: scanned {total_files} files, "
        "no raw session setup outside datapulse.core.db."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
