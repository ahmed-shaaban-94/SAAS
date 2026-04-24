"""Dump FastAPI OpenAPI schema to contracts/openapi.json.

Source of truth for the frontend TypeScript client (issue #658). Run after
any change to a Pydantic response model or route signature; the file it
writes is the input to ``npm run codegen`` in the frontend.

Usage:
    python scripts/dump_openapi.py              # write contracts/openapi.json
    python scripts/dump_openapi.py --check      # exit 1 if on-disk copy is stale

The ``--check`` form is what CI runs so schema drift is caught at PR time
rather than surfacing as a runtime shape mismatch in the dashboard.

Stdlib only on purpose — mirrors the pattern of ``check_migration_numbers``
and ``check_docs_truth_sources`` so it can run before the full dev-extras
install completes.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from pathlib import Path

# Factory imports fail when APP_ENV/DATABASE_URL are unset because the settings
# layer runs eagerly. Pin safe defaults before importing anything datapulse.*.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("SENTRY_ENVIRONMENT", "test")

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "contracts" / "openapi.json"


def build_schema() -> str:
    """Return the serialized OpenAPI schema as a deterministic JSON string."""
    # Deferred import: keeps stdlib-only imports above and lets the env shim run
    # before datapulse.config reads DATABASE_URL.
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from datapulse.api.app import create_app  # noqa: E402

    app = create_app()
    schema = app.openapi()
    # sort_keys so Pydantic's anyOf/allOf ordering cannot cause false drift.
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def check(path: Path, fresh: str) -> int:
    if not path.exists():
        print(f"::error::{path} is missing. Run `make openapi` and commit.", file=sys.stderr)
        return 1
    on_disk = path.read_text(encoding="utf-8")
    if on_disk == fresh:
        return 0
    diff = difflib.unified_diff(
        on_disk.splitlines(keepends=True),
        fresh.splitlines(keepends=True),
        fromfile=f"{path} (committed)",
        tofile=f"{path} (regenerated)",
        n=3,
    )
    sys.stdout.writelines(diff)
    print(
        f"\n::error::OpenAPI contract is stale. Run `make openapi` and commit {path}.",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the committed contract differs from the current schema.",
    )
    args = parser.parse_args()

    fresh = build_schema()
    if args.check:
        return check(CONTRACT_PATH, fresh)

    write(CONTRACT_PATH, fresh)
    print(f"Wrote {CONTRACT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
