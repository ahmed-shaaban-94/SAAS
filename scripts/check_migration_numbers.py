"""CI guard: block PRs that introduce duplicate migration numbers.

Every file in ``migrations/`` is identified by the token before its first
underscore: ``031_pipeline_last_completed_stage.sql`` has key ``031``,
``030a_bronze_sales_unique_index.sql`` has key ``030a``. Two files sharing
a key are duplicates — a numbered-migration runner that keys off the
leading prefix can silently skip one. See issue #538.

Letter suffixes (``030a``, ``030b``, ``071b``) are a valid sub-slot
convention in this repo: they allow adding a follow-up change that must
apply in a specific ordinal position. They are NOT duplicates of their
base number (``030`` and ``030a`` are distinct slots).

Known pre-existing duplicates that predate this guard are grandfathered
via ``migrations/.known-duplicate-prefixes`` (one prefix per line,
``#`` comments allowed). Listed prefixes emit a WARNING (not an error) so
the debt stays visible without blocking every PR. New duplicates — any
prefix with >1 file that ISN'T listed — fail CI.

Exit codes:
    0 — all migration prefixes are unique, or only known-duplicate debt
    1 — one or more NEW duplicates, or malformed filenames

Run locally:
    python scripts/check_migration_numbers.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_KNOWN_DUPES_FILE = MIGRATIONS_DIR / ".known-duplicate-prefixes"
# Accept NNN_* (strict numeric) and NNN<letter>_* (sub-slot variant).
_FILE_RE = re.compile(r"^(?P<prefix>\d{3}[a-z]?)_(?P<slug>[a-z0-9_]+)\.sql$")


def load_known_duplicates(path: Path) -> set[str]:
    """Parse the allowlist of historic duplicate prefixes.

    Missing file -> empty allowlist (nothing grandfathered). Blank lines
    and ``#`` comments are ignored. Each non-empty line is a prefix
    like ``031`` or ``030a``.
    """
    if not path.is_file():
        return set()
    known: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            known.add(line)
    return known


def collect_migrations(directory: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Return (files-by-prefix, malformed-filenames)."""
    by_prefix: dict[str, list[str]] = defaultdict(list)
    malformed: list[str] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file() or entry.suffix != ".sql":
            continue
        match = _FILE_RE.match(entry.name)
        if not match:
            malformed.append(entry.name)
            continue
        by_prefix[match["prefix"]].append(entry.name)
    return by_prefix, malformed


def partition_duplicates(
    by_prefix: dict[str, list[str]],
    known: set[str],
) -> tuple[list[str], list[str]]:
    """Return (new_duplicate_problems, grandfathered_warnings)."""
    new_problems: list[str] = []
    grandfathered: list[str] = []
    for prefix in sorted(by_prefix):
        files = by_prefix[prefix]
        if len(files) <= 1:
            continue
        msg = f"Duplicate migration prefix {prefix!r}: {', '.join(files)}"
        if prefix in known:
            grandfathered.append(msg)
        else:
            new_problems.append(msg)
    return new_problems, grandfathered


def find_malformed_problems(malformed: list[str]) -> list[str]:
    return [
        (
            f"Malformed migration filename {name!r}: "
            "expected pattern NNN_desc.sql or NNN<letter>_desc.sql "
            "(lowercase letters, digits, underscores only)"
        )
        for name in malformed
    ]


def main() -> int:
    if not MIGRATIONS_DIR.is_dir():
        print(f"ERROR: migrations directory not found at {MIGRATIONS_DIR}", file=sys.stderr)
        return 1

    by_prefix, malformed = collect_migrations(MIGRATIONS_DIR)
    known = load_known_duplicates(_KNOWN_DUPES_FILE)
    new_duplicate_problems, grandfathered_warnings = partition_duplicates(by_prefix, known)
    malformed_problems = find_malformed_problems(malformed)
    problems = malformed_problems + new_duplicate_problems

    if grandfathered_warnings:
        print(
            f"WARNING: {len(grandfathered_warnings)} pre-existing duplicate prefix(es) "
            f"still on record in {_KNOWN_DUPES_FILE.name} "
            "(reconcile per RUNBOOK section 3):",
        )
        for w in grandfathered_warnings:
            print(f"  - {w}")

    if problems:
        print(
            f"\nMigration integrity check FAILED ({len(problems)} new problem(s)):",
            file=sys.stderr,
        )
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nSee docs/RUNBOOK.md section 3 for the duplicate-prefix "
            "reconciliation procedure (issue #538).",
            file=sys.stderr,
        )
        return 1

    total = sum(len(files) for files in by_prefix.values())
    print(
        f"Migration integrity check PASSED: {total} files, "
        f"no NEW duplicates (grandfathered: {len(grandfathered_warnings)})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
