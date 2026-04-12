"""Session end handler — ported from brain-session-end.sh.

Entry point: python -m datapulse.brain.session_end

Called by the Stop hook to capture session data into PostgreSQL.
Falls back to markdown files if the database is unavailable.
"""

from __future__ import annotations

import csv
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

# ── Layer / module detection ────────────────────────────────────────

LAYER_RULES: list[tuple[str, list[str]]] = [
    ("bronze", [
        "migrations/", "src/datapulse/bronze/", "src/datapulse/import_pipeline/",
    ]),
    ("silver", ["dbt/models/staging/", "dbt/models/bronze/"]),
    ("gold", [
        "dbt/models/marts/", "src/datapulse/analytics/",
        "src/datapulse/forecasting/", "src/datapulse/targets/",
    ]),
    ("api", ["src/datapulse/api/"]),
    ("frontend", ["frontend/"]),
    ("test", ["tests/", "frontend/e2e/"]),
]

_MODULE_RE = re.compile(r"^src/datapulse/([^/]+)/")
_HARDCODED_MODULES = {
    "dbt/": "dbt",
    "frontend/": "frontend",
    "migrations/": "migrations",
}


def detect_layers_modules(
    files: list[str],
) -> tuple[list[str], list[str]]:
    """Detect layers and modules from a list of file paths."""
    layers: set[str] = set()
    modules: set[str] = set()

    for f in files:
        for layer_name, prefixes in LAYER_RULES:
            if any(f.startswith(p) for p in prefixes):
                layers.add(layer_name)

        m = _MODULE_RE.match(f)
        if m and not m.group(1).startswith("__"):
            modules.add(m.group(1))

        for prefix, mod_name in _HARDCODED_MODULES.items():
            if f.startswith(prefix):
                modules.add(mod_name)

    return sorted(layers), sorted(modules)


LAYER_DESCRIPTIONS = {
    "bronze": "- [[bronze]] -- raw data ingestion changes",
    "silver": "- [[silver]] -- staging/cleaning changes",
    "gold": "- [[gold]] -- analytics/aggregation changes",
    "api": "- [[api]] -- route/service changes",
    "frontend": "- [[frontend]] -- dashboard/UI changes",
    "test": "- [[test]] -- test additions/fixes",
}


# ── Git helpers ─────────────────────────────────────────────────────


def _run(cmd: list[str], cwd: str | None = None) -> str:
    """Run a command and return stripped stdout, or empty string on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def gather_git_data(project_dir: str) -> dict:
    """Gather branch, diff files, and recent commits from git."""
    branch = _run(["git", "branch", "--show-current"], cwd=project_dir) or "detached"
    user_name = _run(["git", "config", "user.name"], cwd=project_dir) or ""

    diff_files = _run(["git", "diff", "--name-only", "HEAD"], cwd=project_dir)
    recent_commits_raw = _run(
        ["git", "log", "--oneline", "--since=4 hours ago", "--max-count=20"],
        cwd=project_dir,
    )

    all_files: set[str] = set()
    if diff_files:
        all_files.update(diff_files.splitlines())

    commits: list[dict[str, str]] = []
    if recent_commits_raw:
        for line in recent_commits_raw.splitlines():
            parts = line.split(" ", 1)
            sha = parts[0]
            message = parts[1] if len(parts) > 1 else ""
            commits.append({"sha": sha, "message": message})
            commit_files = _run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
                cwd=project_dir,
            )
            if commit_files:
                all_files.update(commit_files.splitlines())

    files_list = sorted(f for f in all_files if f)

    return {
        "branch": branch,
        "user_name": user_name,
        "files": files_list,
        "commits": commits,
        "recent_commits_raw": recent_commits_raw,
    }


# ── Markdown builders ───────────────────────────────────────────────


def build_body_md(
    *,
    timestamp: str,
    files: list[str],
    commits_raw: str,
    layers: list[str],
    modules: list[str],
) -> str:
    """Build the session note markdown body."""
    # Files section (truncate at 50)
    if len(files) > 50:
        files_section = "\n".join(f"- {f}" for f in files[:50])
        files_section += f"\n- ... and {len(files) - 50} more"
    else:
        files_section = "\n".join(f"- {f}" for f in files) if files else "_No files changed._"

    # Commits section
    if commits_raw:
        commits_section = "\n".join(f"- {line}" for line in commits_raw.splitlines())
    else:
        commits_section = "_No commits in this session._"

    # Layers section
    if layers:
        layers_section = "\n".join(
            LAYER_DESCRIPTIONS.get(ly, f"- [[{ly}]]") for ly in layers
        )
    else:
        layers_section = "_No recognized layers._"

    # Modules section
    if modules:
        modules_section = "\n".join(f"- [[{m}]]" for m in modules)
    else:
        modules_section = "_No recognized modules._"

    return f"""# Session {timestamp}

## Files Changed
{files_section}

## Commits
{commits_section}

## Layers Touched
{layers_section}

## Modules Touched
{modules_section}
"""


def build_index_md(sessions: list[dict]) -> str:
    """Build _INDEX.md from a list of session dicts (from DB or files)."""
    updated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M")

    if not sessions:
        return f"""---
generated: true
last_updated: {updated}
---
# DataPulse Second Brain -- Context Index

> Auto-generated by brain session-end hook.
> Claude reads this at the start of every session for recent context.

## Recent Sessions

_No sessions recorded yet._
"""

    entries = []
    for s in sessions:
        ts = s.get("timestamp", "unknown")
        if hasattr(ts, "strftime"):
            ts = ts.strftime("%Y-%m-%dT%H:%M")
        branch = s.get("branch", "unknown")
        layers = s.get("layers", [])
        modules = s.get("modules", [])
        layers_str = "[" + ",".join(layers) + "]" if layers else "[]"
        modules_str = "[" + ",".join(modules) + "]" if modules else "[]"

        entries.append(f"""### {ts}
- **Branch**: `{branch}`
- **Layers**: {layers_str}
- **Modules**: {modules_str}
""")

    entries_block = "\n".join(entries)

    return f"""---
generated: true
last_updated: {updated}
---
# DataPulse Second Brain -- Context Index

> Auto-generated by brain session-end hook.
> Claude reads this at the start of every session for recent context.

## Recent Sessions (last 5)

{entries_block}
## Vault Structure

- `sessions/` -- Auto-generated session notes
- `layers/` -- Medallion layer notes
- `modules/` -- Per-module knowledge
- `decisions/` -- Decision records (brain.decisions table)
- `incidents/` -- Post-incident analyses (brain.incidents table)
"""


# ── File-based fallback ─────────────────────────────────────────────


def write_session_file(
    session_dir: Path,
    *,
    timestamp: str,
    filename: str,
    branch: str,
    layers: list[str],
    modules: list[str],
    body_md: str,
) -> None:
    """Write a session markdown file (fallback when DB is down)."""
    session_dir.mkdir(parents=True, exist_ok=True)
    layers_yaml = ",".join(layers)
    modules_yaml = ",".join(modules)

    content = f"""---
date: {timestamp}
branch: {branch}
layers: [{layers_yaml}]
modules: [{modules_yaml}]
---
{body_md}
"""
    (session_dir / f"{filename}.md").write_text(content, encoding="utf-8")


def write_index_from_files(brain_dir: Path) -> None:
    """Regenerate _INDEX.md from the last 5 session files."""
    session_dir = brain_dir / "sessions"
    files = sorted(session_dir.glob("*.md"), reverse=True)[:5]

    sessions = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        frontmatter: dict[str, str] = {}
        for line in text.splitlines():
            if line.startswith("---"):
                if frontmatter:
                    break
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                frontmatter[key.strip()] = val.strip()
        layers_raw = frontmatter.get("layers", "[]").strip("[]")
        modules_raw = frontmatter.get("modules", "[]").strip("[]")
        sessions.append({
            "timestamp": frontmatter.get("date", "unknown"),
            "branch": frontmatter.get("branch", "unknown"),
            "layers": [x.strip() for x in layers_raw.split(",") if x.strip()],
            "modules": [x.strip() for x in modules_raw.split(",") if x.strip()],
        })

    (brain_dir / "_INDEX.md").write_text(build_index_md(sessions), encoding="utf-8")


def append_csv(brain_dir: Path, *, timestamp: str, branch: str, user_name: str,
               layers: list[str], modules: list[str]) -> None:
    """Append a row to session-log.csv for backward compatibility."""
    csv_path = brain_dir / "session-log.csv"
    write_header = not csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "branch", "user", "layers", "modules"])
        layers_str = "[" + ";".join(layers) + "]"
        modules_str = "[" + ";".join(modules) + "]"
        writer.writerow([timestamp, branch, user_name, layers_str, modules_str])


# ── Main entry point ────────────────────────────────────────────────


def main() -> None:
    """Capture session data into PostgreSQL (or markdown fallback)."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        project_dir = _run(["git", "rev-parse", "--show-toplevel"])
    if not project_dir:
        return

    project_path = Path(project_dir)
    brain_dir = project_path / "docs" / "brain"
    session_dir = brain_dir / "sessions"

    # Load .env for DATABASE_URL and OPENROUTER_API_KEY
    try:
        from dotenv import load_dotenv
        load_dotenv(project_path / ".env")
    except ImportError:
        pass

    # Gather git data
    git_data = gather_git_data(project_dir)

    # Skip if nothing happened
    if not git_data["files"] and not git_data["commits"]:
        return

    layers, modules = detect_layers_modules(git_data["files"])

    now = datetime.now(UTC)
    timestamp = now.strftime("%Y-%m-%dT%H:%M")
    filename = now.strftime("%Y-%m-%d-%H-%M")

    body_md = build_body_md(
        timestamp=timestamp,
        files=git_data["files"],
        commits_raw=git_data["recent_commits_raw"],
        layers=layers,
        modules=modules,
    )

    # Try PostgreSQL path
    db_ok = False
    try:
        from datapulse.brain.db import get_recent_sessions, insert_session, update_embedding

        session_id = insert_session(
            timestamp=timestamp,
            branch=git_data["branch"],
            user_name=git_data["user_name"],
            layers=layers,
            modules=modules,
            files_changed=git_data["files"],
            commits=git_data["commits"],
            body_md=body_md,
        )

        # Generate embedding (non-blocking, nullable)
        try:
            from datapulse.brain.embeddings import get_embedding
            vec = get_embedding(body_md)
            if vec is not None:
                update_embedding("sessions", session_id, vec)
        except Exception:
            pass  # Embedding is optional

        # Regenerate _INDEX.md from DB
        recent = get_recent_sessions(count=5)
        brain_dir.mkdir(parents=True, exist_ok=True)
        (brain_dir / "_INDEX.md").write_text(
            build_index_md(recent), encoding="utf-8",
        )
        db_ok = True

    except Exception:
        # DB unavailable — fall back to file-based approach
        pass

    if not db_ok:
        # Markdown fallback
        write_session_file(
            session_dir,
            timestamp=timestamp,
            filename=filename,
            branch=git_data["branch"],
            layers=layers,
            modules=modules,
            body_md=body_md,
        )
        write_index_from_files(brain_dir)

    # Always append CSV for backward compatibility
    append_csv(
        brain_dir,
        timestamp=timestamp,
        branch=git_data["branch"],
        user_name=git_data["user_name"],
        layers=layers,
        modules=modules,
    )

    # Auto-stage brain files
    _run(["git", "add", "docs/brain/sessions/", "docs/brain/_INDEX.md",
          "docs/brain/session-log.csv"], cwd=project_dir)


if __name__ == "__main__":
    main()
