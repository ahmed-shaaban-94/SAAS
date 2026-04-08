"""Indexer orchestrator — scans the full DataPulse codebase and builds the graph.

Usage:
    python -m datapulse.graph.indexer [--project-root /path/to/Data-Pulse]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from datapulse.graph import store
from datapulse.graph.analyzers.dbt_analyzer import analyze_dbt_project
from datapulse.graph.analyzers.python_analyzer import analyze_python_project
from datapulse.graph.analyzers.typescript_analyzer import analyze_frontend_project


def index(project_root: str | None = None, full_rebuild: bool = True) -> dict:
    """Index the full DataPulse project and return stats."""
    if project_root is None:
        project_root = str(Path(__file__).resolve().parents[3])

    t0 = time.monotonic()

    store.init_db()
    if full_rebuild:
        store.clear()

    dbt_count = analyze_dbt_project(project_root)
    py_count = analyze_python_project(project_root)
    ts_count = analyze_frontend_project(project_root)

    elapsed = time.monotonic() - t0
    graph_stats = store.stats()

    return {
        "project_root": project_root,
        "files_indexed": {
            "dbt_models": dbt_count,
            "python_files": py_count,
            "typescript_files": ts_count,
            "total": dbt_count + py_count + ts_count,
        },
        "graph": graph_stats,
        "elapsed_seconds": round(elapsed, 2),
    }


def main() -> None:
    root = None
    if len(sys.argv) > 2 and sys.argv[1] == "--project-root":
        root = sys.argv[2]

    print("DataPulse Graph — Indexing codebase...")
    result = index(root)
    print(f"Done in {result['elapsed_seconds']}s")
    print(
        f"Files: {result['files_indexed']['total']} "
        f"(dbt:{result['files_indexed']['dbt_models']} "
        f"py:{result['files_indexed']['python_files']} "
        f"ts:{result['files_indexed']['typescript_files']})"
    )
    print(
        f"Graph: {result['graph']['total_symbols']} symbols, {result['graph']['total_edges']} edges"
    )
    print(f"Layers: {result['graph']['by_layer']}")
    print(f"Kinds:  {result['graph']['by_kind']}")


if __name__ == "__main__":
    main()
