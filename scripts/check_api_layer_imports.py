"""CI guard: block new ``from datapulse.api.*`` imports outside ``api/``.

Issue #541. The dependency rule in ``.claude/rules/datapulse-graph.md``
forbids business modules from importing out of ``api/``. Business modules
are ``analytics/``, ``pipeline/``, ``billing/``, ``pos/``, ``rbac/``,
``tasks/``, and any other non-``api/`` package under ``src/datapulse/``.

This guard walks every ``.py`` file under ``src/datapulse/`` and flags
any import of the form ``from datapulse.api.<...>`` or
``import datapulse.api<...>`` that appears OUTSIDE ``src/datapulse/api/``.

Known pre-existing offenders are grandfathered via
``scripts/.known-api-layer-violations`` (one path per line, ``#`` comments
allowed, paths are POSIX-style relative to the repo root). Listed paths
emit a WARNING so the debt stays visible without blocking every PR. Any
NEW offender — a path that isn't listed — fails CI.

Exit codes:
    0 — clean, or only grandfathered offenders
    1 — one or more NEW offenders

Run locally:
    python scripts/check_api_layer_imports.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_TARGET_DIR = REPO_ROOT / "src" / "datapulse"
_API_DIR = _TARGET_DIR / "api"
_KNOWN_VIOLATIONS_FILE = Path(__file__).resolve().parent / ".known-api-layer-violations"

# Matches either:
#   from datapulse.api.deps import X
#   from datapulse.api import deps
#   import datapulse.api.deps
# but NOT bare `import datapulse` (not a layer violation on its own).
_IMPORT_RE = re.compile(
    r"^[ \t]*(?:from\s+datapulse\.api(?:\.\w+)*\s+import\b|import\s+datapulse\.api(?:\.\w+)+)",
    re.MULTILINE,
)


def load_known_violations(path: Path) -> set[str]:
    """Parse the allowlist. Missing file -> empty allowlist."""
    if not path.is_file():
        return set()
    known: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            known.add(line)
    return known


def _posix_relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def find_offenders(target_dir: Path, api_dir: Path) -> dict[str, list[tuple[int, str]]]:
    """Scan every ``.py`` file under ``target_dir`` (skipping ``api_dir``).

    Returns a mapping ``{posix_path: [(lineno, line_text), ...]}``.
    """
    offenders: dict[str, list[tuple[int, str]]] = {}
    for py_file in sorted(target_dir.rglob("*.py")):
        try:
            py_file.relative_to(api_dir)
            continue  # inside api/ — allowed
        except ValueError:
            pass  # outside api/ — subject to the rule
        text = py_file.read_text(encoding="utf-8")
        hits: list[tuple[int, str]] = []
        for match in _IMPORT_RE.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            line_text = text.splitlines()[lineno - 1].strip()
            hits.append((lineno, line_text))
        if hits:
            offenders[_posix_relative(py_file)] = hits
    return offenders


def partition(
    offenders: dict[str, list[tuple[int, str]]],
    known: set[str],
) -> tuple[list[str], list[str]]:
    """Split offender messages into (new_problems, grandfathered)."""
    new_problems: list[str] = []
    grandfathered: list[str] = []
    for rel_path in sorted(offenders):
        for lineno, line in offenders[rel_path]:
            msg = f"{rel_path}:{lineno}: {line}"
            (grandfathered if rel_path in known else new_problems).append(msg)
    return new_problems, grandfathered


def main() -> int:
    if not _TARGET_DIR.is_dir():
        print(f"ERROR: target directory not found at {_TARGET_DIR}", file=sys.stderr)
        return 1

    offenders = find_offenders(_TARGET_DIR, _API_DIR)
    known = load_known_violations(_KNOWN_VIOLATIONS_FILE)
    new_problems, grandfathered = partition(offenders, known)

    if grandfathered:
        print(
            f"WARNING: {len(grandfathered)} pre-existing api-layer import(s) "
            f"still on record in {_KNOWN_VIOLATIONS_FILE.name} "
            "(see issue #541 for the full-move follow-up):",
        )
        for w in grandfathered:
            print(f"  - {w}")

    if new_problems:
        print(
            f"\nAPI-layer import check FAILED ({len(new_problems)} new violation(s)):",
            file=sys.stderr,
        )
        for p in new_problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nBusiness modules must not import from `datapulse.api.*`. "
            "Move the symbol to `datapulse.core` / `datapulse.config`, or add "
            "the file to scripts/.known-api-layer-violations with a reason. "
            "Rule: .claude/rules/datapulse-graph.md §Layer Ordering.",
            file=sys.stderr,
        )
        return 1

    total_files = sum(1 for _ in _TARGET_DIR.rglob("*.py"))
    print(
        f"API-layer import check PASSED: scanned {total_files} files, "
        f"no NEW violations (grandfathered: {len(grandfathered)})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
