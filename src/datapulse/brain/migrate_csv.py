"""One-time migration: import existing session-log.csv + session markdown files into PostgreSQL.

Usage:
    PYTHONPATH=src python -m datapulse.brain.migrate_csv [--project-dir /path/to/datapulse]
"""

from __future__ import annotations

import csv
from pathlib import Path

from datapulse.brain.db import insert_session


def parse_session_file(path: Path) -> dict | None:
    """Parse a session markdown file and return a dict for insert_session."""
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter: dict[str, str] = {}
    in_fm = False

    for line in text.splitlines():
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm and ":" in line:
            key, _, val = line.partition(":")
            frontmatter[key.strip()] = val.strip()

    if not frontmatter.get("date"):
        return None

    layers_raw = frontmatter.get("layers", "[]").strip("[]")
    modules_raw = frontmatter.get("modules", "[]").strip("[]")

    # Extract body (everything after second ---)
    body_start = text.find("---", text.find("---") + 3)
    body_md = text[body_start + 3:].strip() if body_start > 0 else ""

    return {
        "timestamp": frontmatter["date"],
        "branch": frontmatter.get("branch", "unknown"),
        "user_name": "",
        "layers": [x.strip() for x in layers_raw.split(",") if x.strip()],
        "modules": [x.strip() for x in modules_raw.split(",") if x.strip()],
        "files_changed": [],
        "commits": [],
        "body_md": body_md,
    }


def parse_csv_row(row: dict) -> dict | None:
    """Parse a CSV row from session-log.csv."""
    if not row.get("timestamp"):
        return None

    layers_raw = row.get("layers", "[]").strip("[]")
    modules_raw = row.get("modules", "[]").strip("[]")

    return {
        "timestamp": row["timestamp"],
        "branch": row.get("branch", "unknown"),
        "user_name": row.get("user", ""),
        "layers": [x.strip() for x in layers_raw.split(";") if x.strip()],
        "modules": [x.strip() for x in modules_raw.split(";") if x.strip()],
        "files_changed": [],
        "commits": [],
        "body_md": "",
    }


def migrate(project_dir: Path) -> None:
    """Import existing brain data into PostgreSQL."""
    brain_dir = project_dir / "docs" / "brain"
    imported = 0

    # Import session markdown files
    session_dir = brain_dir / "sessions"
    if session_dir.exists():
        for f in sorted(session_dir.glob("*.md")):
            if f.name == ".gitkeep":
                continue
            data = parse_session_file(f)
            if data:
                try:
                    sid = insert_session(**data)
                    print(f"  [OK] {f.name} -> session {sid}")
                    imported += 1
                except Exception as exc:
                    print(f"  [SKIP] {f.name}: {exc}")

    # Import CSV rows (may duplicate markdown imports — that's OK for a one-time migration)
    csv_path = brain_dir / "session-log.csv"
    if csv_path.exists():
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data = parse_csv_row(row)
                if data:
                    try:
                        sid = insert_session(**data)
                        print(f"  [OK] CSV row {data['timestamp']} -> session {sid}")
                        imported += 1
                    except Exception as exc:
                        print(f"  [SKIP] CSV row: {exc}")

    print(f"\nMigrated {imported} records into brain.sessions.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate brain data to PostgreSQL")
    parser.add_argument("--project-dir", default=".", help="Project root directory")
    args = parser.parse_args()

    project_path = Path(args.project_dir).resolve()

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv(project_path / ".env")
    except ImportError:
        pass

    print(f"Migrating brain data from {project_path / 'docs' / 'brain'} ...")
    migrate(project_path)
