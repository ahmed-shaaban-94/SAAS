#!/usr/bin/env python3
"""Migration safety linter — flags dangerous DDL patterns that cause downtime.

Checks SQL migrations for operations that can lock a live Postgres table:

  • ADD COLUMN ... NOT NULL without a DEFAULT (table rewrite / lock)
  • CREATE INDEX without CONCURRENTLY on an existing table
  • ALTER COLUMN ... TYPE (table rewrite + AccessExclusive lock)
  • DROP COLUMN (destructive)
  • TRUNCATE (destructive)
  • LOCK TABLE (explicit escalation)

Suppression: add `-- migration-safety: ok` on the same line as a flagged
statement to silence that specific instance (e.g. for CREATE TABLE blocks
where an index on a fresh table is safe, or migrations run outside a tx).

Exit codes: 0 = clean, 1 = errors found.

Usage:
  python scripts/check_migration_safety.py               # check all migrations/
  python scripts/check_migration_safety.py migrations/105_*.sql  # specific files
  git diff --name-only origin/main...HEAD | grep ^migrations/ \\
    | xargs python scripts/check_migration_safety.py     # only PR-changed files
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── Suppression tag ───────────────────────────────────────────────────────────
# Add this anywhere on the same line as the statement to suppress the check.
SUPPRESSION_TAG = re.compile(r"--\s*migration-safety:\s*ok", re.IGNORECASE)

# ── Rules ─────────────────────────────────────────────────────────────────────
# (line_pattern, message, severity)
LINE_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            r"\bCREATE\s+INDEX\b(?!\s+CONCURRENTLY\b|\s+IF\s+NOT\s+EXISTS\b\s+\S+\s+ON\b|\s+\S+\s+ON\b\s+ONLY\b)",
            re.IGNORECASE,
        ),
        "CREATE INDEX without CONCURRENTLY holds an AccessShareLock. "
        "Use CONCURRENTLY (requires running outside a transaction) "
        "— or add '-- migration-safety: ok' if the table was just created "
        "in this same migration.",
        "error",
    ),
    (
        re.compile(
            r"\bALTER\s+TABLE\b[^;\n]+\bADD\s+COLUMN\b[^;\n]+\bNOT\s+NULL\b(?![^;\n]*\bDEFAULT\b)",
            re.IGNORECASE,
        ),
        "ADD COLUMN NOT NULL without DEFAULT requires a table rewrite on PG < 11 "
        "and still needs a DEFAULT on PG 11+ for a metadata-only change. "
        "Add a literal DEFAULT or use a nullable column + backfill + constraint.",
        "error",
    ),
    (
        re.compile(
            r"\bALTER\s+(?:TABLE\s+\S+\s+)?ALTER\s+COLUMN\b[^;\n]+\bSET\s+DATA\s+TYPE\b|\bTYPE\s+\w",
            re.IGNORECASE,
        ),
        "ALTER COLUMN TYPE rewrites the table and holds AccessExclusive for the duration. "
        "Add a new column, backfill in batches, then swap.",
        "error",
    ),
    (
        re.compile(r"^\s*TRUNCATE\b", re.IGNORECASE),
        "TRUNCATE in a migration removes all rows permanently. "
        "Migrations should be forward-safe — never truncate in a forward migration.",
        "error",
    ),
    (
        re.compile(r"\bLOCK\s+TABLE\b", re.IGNORECASE),
        "Explicit LOCK TABLE can cause deadlocks. Remove it and rely on implicit locking.",
        "error",
    ),
    (
        re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
        "DROP COLUMN is destructive — data is permanently removed. "
        "Ensure the column is unused before applying.",
        "warning",
    ),
    (
        re.compile(
            r"\bDROP\s+TABLE\b(?!\s+IF\s+EXISTS\b)",
            re.IGNORECASE,
        ),
        "DROP TABLE (without IF EXISTS) fails on missing tables. Use DROP TABLE IF EXISTS.",
        "warning",
    ),
]


def check_file(path: Path) -> list[tuple[str, str, str, int]]:
    """Return (severity, message, line_text, lineno) for each violation."""
    violations: list[tuple[str, str, str, int]] = []
    lines = path.read_text(encoding="utf-8").splitlines()

    # Track whether we're inside a block comment
    in_block_comment = False

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line

        # Skip/strip block comments
        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
                line = line[line.index("*/") + 2 :]
            else:
                continue
        if "/*" in line:
            if "*/" in line[line.index("/*") :]:
                # Same-line block comment
                before = line[: line.index("/*")]
                after_end = line.index("*/", line.index("/*")) + 2
                line = before + line[after_end:]
            else:
                line = line[: line.index("/*")]
                in_block_comment = True

        # Strip line comment
        if "--" in line:
            line = line[: line.index("--")]

        # Skip blank lines
        if not line.strip():
            continue

        # Apply rules against the original raw_line (for suppression tag check)
        for pattern, message, severity in LINE_RULES:
            if pattern.search(line):
                # Check for suppression tag on the same raw line
                if SUPPRESSION_TAG.search(raw_line):
                    continue
                violations.append((severity, message, raw_line.rstrip(), lineno))

    return violations


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        paths = [Path(p) for p in argv[1:] if p]
    else:
        migrations_dir = Path(__file__).parent.parent / "migrations"
        if not migrations_dir.exists():
            print(f"migrations/ directory not found at {migrations_dir}", file=sys.stderr)
            return 1
        paths = sorted(migrations_dir.glob("*.sql"))

    if not paths:
        print("No migration files to check.")
        return 0

    error_count = 0
    warning_count = 0

    for path in paths:
        if not path.exists():
            print(f"::error::File not found: {path}", file=sys.stderr)
            error_count += 1
            continue
        violations = check_file(path)
        for severity, message, line_text, lineno in violations:
            gha_level = "error" if severity == "error" else "warning"
            print(f"::{gha_level} file={path},line={lineno}::{severity.upper()}: {message}")
            print(f"  Line {lineno}: {line_text.strip()!r}")
            if severity == "error":
                error_count += 1
            else:
                warning_count += 1

    total = len(paths)
    if error_count == 0 and warning_count == 0:
        print(f"Migration safety: {total} file(s) checked — no violations.")
        return 0

    print(
        f"\nMigration safety: {error_count} error(s), {warning_count} warning(s) "
        f"across {total} file(s). "
        "Add '-- migration-safety: ok' to suppress known-safe patterns.",
    )
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
