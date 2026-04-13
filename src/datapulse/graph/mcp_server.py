"""DataPulse Graph + Brain MCP Server — 11 tools for Claude Code integration.

Graph tools:
    dp_impact   — Blast radius: what breaks if I change X?
    dp_context  — 360-degree view of any symbol
    dp_query    — Search the code graph
    dp_detect_changes — Map git diff to affected symbols

Brain tools:
    brain_search          — Hybrid FTS + semantic search across all brain tables
    brain_recent          — Get the most recent sessions
    brain_session         — Full detail of a single session
    brain_log_decision    — Record a decision
    brain_log_incident    — Record an incident
    brain_log_knowledge   — Store static project knowledge (architecture, API docs, runbooks, etc.)
    brain_knowledge_search — Search the project knowledge base by keyword and/or category

Usage:
    python -m datapulse.graph.mcp_server
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from datapulse.graph import store
from datapulse.graph.indexer import index

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("datapulse-graph")
except ImportError:
    mcp = None  # type: ignore[assignment]

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])


def _tool():
    """Decorator that registers with MCP if available, otherwise no-op."""
    if mcp is not None:
        return mcp.tool()
    return lambda fn: fn


@_tool()
def dp_impact(
    symbol_name: str,
    max_depth: int = 3,
) -> str:
    """Blast radius analysis: what gets affected if you change a symbol?

    Works across medallion layers (bronze → silver → gold → API → frontend).
    Returns affected symbols grouped by depth with layer information.

    Args:
        symbol_name: Name of the function, class, dbt model, or component to analyze.
                     Examples: "calculate_revenue", "stg_sales", "dim_customer",
                              "AnalyticsRepository", "useRevenue"
        max_depth: How many hops to traverse (1-5). Default 3.
    """
    _ensure_indexed()
    result = store.impact_query(symbol_name, max_depth=max_depth)

    if not result:
        return json.dumps(
            {
                "error": f"No symbol matching '{symbol_name}' found",
                "hint": "Try a partial name or use dp_query to search first",
            }
        )

    total = sum(len(v) for v in result.values())
    output: dict[str, Any] = {"symbol": symbol_name, "total_affected": total, "by_depth": {}}
    for depth, hits in result.items():
        by_layer: dict[str, list] = {}
        for h in hits:
            layer = h.get("layer", "unknown")
            by_layer.setdefault(layer, []).append(
                {
                    "name": h["name"],
                    "kind": h["kind"],
                    "file": h["file"],
                    "line": h["line"],
                    "relationship": h["relationship"],
                }
            )
        output["by_depth"][f"depth_{depth}"] = by_layer

    return json.dumps(output, indent=2)


@_tool()
def dp_context(
    symbol_name: str,
) -> str:
    """360-degree view of a symbol: callers, callees, imports, tests, layer.

    Shows everything related to a symbol in one query — who calls it,
    what it calls, what tests cover it, which layer it belongs to.

    Args:
        symbol_name: Name of the symbol to inspect.
                     Examples: "get_revenue_summary", "fct_sales",
                              "ChartCard", "useTopProducts"
    """
    _ensure_indexed()
    result = store.context_query(symbol_name)
    return json.dumps(result, indent=2)


@_tool()
def dp_query(
    query: str,
    kind: str | None = None,
    layer: str | None = None,
) -> str:
    """Search the code graph for symbols matching a query.

    Args:
        query: Search term (partial match supported).
               Examples: "revenue", "customer", "sales"
        kind: Filter by symbol type. Options: function, class, method,
              hook, component, page, dbt_model, dbt_source, test,
              api_endpoint, module
        layer: Filter by medallion layer. Options: bronze, silver, gold,
               api, frontend, test, backend
    """
    _ensure_indexed()
    results = store.search_query(query, kind=kind, layer=layer)

    if not results:
        return json.dumps(
            {
                "results": [],
                "hint": f"No symbols matching '{query}'. Try a broader term.",
            }
        )

    return json.dumps(
        {
            "count": len(results),
            "results": [
                {
                    "name": r["name"],
                    "kind": r["kind"],
                    "file": r["file_path"],
                    "line": r["line_number"],
                    "layer": r["layer"],
                    "module": r["module"],
                }
                for r in results
            ],
        },
        indent=2,
    )


@_tool()
def dp_detect_changes() -> str:
    """Map current git changes to affected symbols and their dependencies.

    Reads `git diff --name-only` to find changed files, then traces
    which symbols are defined in those files and what depends on them.
    Run this before committing to understand the blast radius.
    """
    _ensure_indexed()

    try:
        diff_result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=_PROJECT_ROOT,
            timeout=10,
        )
        staged_result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True,
            text=True,
            cwd=_PROJECT_ROOT,
            timeout=10,
        )
        untracked_result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=_PROJECT_ROOT,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "git command timed out"})

    changed_files: set[str] = set()
    for r in (diff_result, staged_result, untracked_result):
        if r.returncode == 0:
            changed_files.update(f.strip() for f in r.stdout.strip().split("\n") if f.strip())

    if not changed_files:
        return json.dumps({"message": "No changes detected", "changed_files": []})

    affected: list[dict] = []
    for fpath in sorted(changed_files):
        file_syms = store.find_by_file(fpath)
        for sym in file_syms:
            impact = store.impact_query(sym["name"], max_depth=2)
            downstream_count = sum(len(v) for v in impact.values())
            affected.append(
                {
                    "symbol": sym["name"],
                    "kind": sym["kind"],
                    "file": fpath,
                    "layer": sym["layer"],
                    "downstream_affected": downstream_count,
                }
            )

    # Sort by impact (most downstream affected first)
    affected.sort(key=lambda x: x["downstream_affected"], reverse=True)

    return json.dumps(
        {
            "changed_files": sorted(changed_files),
            "affected_symbols": affected[:30],
            "total_symbols_in_changed_files": len(affected),
            "risk_summary": _risk_summary(affected),
        },
        indent=2,
    )


def _risk_summary(affected: list[dict]) -> str:
    layers = set(a["layer"] for a in affected if a["layer"])
    max_downstream = max((a["downstream_affected"] for a in affected), default=0)

    if max_downstream > 10 or len(layers) > 2:
        return "HIGH — changes span multiple layers with wide blast radius"
    if max_downstream > 5 or len(layers) > 1:
        return "MEDIUM — changes affect multiple components"
    return "LOW — changes are contained"


def _ensure_indexed() -> None:
    """Auto-index if the database is empty."""
    store.init_db()
    s = store.stats()
    if s["total_symbols"] == 0:
        index(_PROJECT_ROOT)


## ── Brain MCP Tools ─────────────────────────────────────────────────


def _brain_error(msg: str) -> str:
    """Return a standard brain error JSON."""
    return json.dumps(
        {
            "error": msg,
            "hint": "Ensure DATABASE_URL is set and PostgreSQL is running",
        }
    )


def _serialize(obj: Any) -> Any:
    """Make objects JSON-serializable (datetimes, Decimals, etc.)."""
    import datetime
    from decimal import Decimal

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


@_tool()
def brain_search(
    query: str,
    layers: list[str] | None = None,
    modules: list[str] | None = None,
    limit: int = 20,
) -> str:
    """Search across all brain sessions, decisions, and incidents.

    Hybrid search: combines full-text (keyword) + semantic (meaning) when
    OPENROUTER_API_KEY is configured. Falls back to FTS-only otherwise.

    Args:
        query: Search terms (natural language, e.g. "bronze loader refactor").
        layers: Filter to sessions touching these layers (e.g. ["bronze", "gold"]).
        modules: Filter to sessions touching these modules (e.g. ["analytics"]).
        limit: Max results to return (default 20).
    """
    try:
        from datapulse.brain import db as brain_db
        from datapulse.brain.embeddings import get_embedding

        query_embedding = get_embedding(query)
        results = brain_db.search_hybrid(
            query,
            query_embedding,
            layers=layers,
            modules=modules,
            limit=limit,
        )
        return json.dumps({"count": len(results), "results": _serialize(results)}, indent=2)
    except Exception as exc:
        return _brain_error(str(exc))


@_tool()
def brain_recent(count: int = 5) -> str:
    """Get the most recent brain sessions.

    Returns the last N sessions with full detail including files changed,
    layers, modules, and commit messages.

    Args:
        count: Number of recent sessions to return (default 5, max 20).
    """
    try:
        from datapulse.brain import db as brain_db

        count = min(max(count, 1), 20)
        sessions = brain_db.get_recent_sessions(count=count)
        return json.dumps({"sessions": _serialize(sessions)}, indent=2)
    except Exception as exc:
        return _brain_error(str(exc))


@_tool()
def brain_session(session_id: int) -> str:
    """Get full detail of a single brain session by ID.

    Returns the session with its linked decisions and incidents.

    Args:
        session_id: The session ID (from brain_recent or brain_search results).
    """
    try:
        from datapulse.brain import db as brain_db

        session = brain_db.get_session_by_id(session_id)
        if session is None:
            return json.dumps({"error": f"Session {session_id} not found"})
        return json.dumps({"session": _serialize(session)}, indent=2)
    except Exception as exc:
        return _brain_error(str(exc))


@_tool()
def brain_log_decision(
    title: str,
    body_md: str = "",
    tags: list[str] | None = None,
    session_id: int | None = None,
) -> str:
    """Log a lightweight decision record to the brain.

    Use for design choices, library selections, trade-off analyses,
    or any decision worth remembering across sessions.

    Args:
        title: Short decision summary (e.g. "Chose psycopg2 over asyncpg").
        body_md: Detailed reasoning in markdown.
        tags: Categorization tags (e.g. ["architecture", "database"]).
        session_id: Optional session to link this decision to.
    """
    try:
        from datapulse.brain import db as brain_db
        from datapulse.brain.embeddings import get_embedding

        row_id = brain_db.insert_decision(
            title=title,
            body_md=body_md,
            tags=tags,
            session_id=session_id,
        )

        # Generate embedding for the decision
        vec = get_embedding(f"{title}\n{body_md}")
        if vec is not None:
            brain_db.update_embedding("decisions", row_id, vec)

        return json.dumps({"id": row_id, "title": title, "status": "created"})
    except Exception as exc:
        return _brain_error(str(exc))


@_tool()
def brain_log_incident(
    title: str,
    body_md: str = "",
    severity: str = "low",
    tags: list[str] | None = None,
    session_id: int | None = None,
) -> str:
    """Log an incident or post-incident note to the brain.

    Use for CI breaks, production issues, data quality problems,
    or security findings discovered during development.

    Args:
        title: Short incident summary.
        body_md: Root cause analysis, resolution steps, lessons learned.
        severity: One of "low", "medium", "high", "critical".
        tags: Categorization tags.
        session_id: Optional session to link this incident to.
    """
    try:
        from datapulse.brain import db as brain_db
        from datapulse.brain.embeddings import get_embedding

        row_id = brain_db.insert_incident(
            title=title,
            body_md=body_md,
            severity=severity,
            tags=tags,
            session_id=session_id,
        )

        # Generate embedding for the incident
        vec = get_embedding(f"{title}\n{body_md}")
        if vec is not None:
            brain_db.update_embedding("incidents", row_id, vec)

        return json.dumps({"id": row_id, "title": title, "severity": severity, "status": "created"})
    except Exception as exc:
        return _brain_error(str(exc))


@_tool()
def brain_log_knowledge(
    title: str,
    body_md: str = "",
    category: str = "general",
    tags: list[str] | None = None,
) -> str:
    """Store a static project knowledge record in the brain.

    Use for architecture documentation, API contracts, dbt model explanations,
    runbooks, onboarding guides, glossary entries, or any reference material
    that should be searchable across future sessions.

    Args:
        title: Short descriptive title (e.g. "Medallion Layers Explained").
        body_md: Full content in markdown — can be as long as needed.
        category: Logical grouping: "architecture", "api", "dbt", "runbook",
                  "onboarding", "glossary", or any custom category.
        tags: Search tags (e.g. ["bronze", "silver", "gold", "dbt"]).
    """
    try:
        from datapulse.brain import db as brain_db
        from datapulse.brain.embeddings import get_embedding

        row_id = brain_db.insert_knowledge(
            title=title,
            body_md=body_md,
            category=category,
            tags=tags,
        )

        vec = get_embedding(f"{title}\n{body_md}")
        if vec is not None:
            brain_db.update_embedding("knowledge", row_id, vec)

        return json.dumps(
            {"id": row_id, "category": category, "title": title, "status": "created"}
        )
    except Exception as exc:
        return _brain_error(str(exc))


@_tool()
def brain_knowledge_search(
    query: str,
    category: str | None = None,
    limit: int = 20,
) -> str:
    """Search the project knowledge base by keyword and optional category.

    Uses full-text search (FTS) with ts_rank scoring. Returns knowledge records
    ranked by relevance. Optionally filter to a specific category.

    Args:
        query: Search terms (e.g. "bronze loader parquet", "auth JWT claims").
        category: Optional filter — "architecture", "api", "dbt", "runbook",
                  "onboarding", "glossary", or any category used when logging.
        limit: Max results to return (default 20).
    """
    try:
        from datapulse.brain import db as brain_db

        results = brain_db.search_knowledge(query, category=category, limit=limit)
        return json.dumps({"count": len(results), "results": _serialize(results)}, indent=2)
    except Exception as exc:
        return _brain_error(str(exc))


# ── Server entry point ───────────────────────────────────────────────


def main() -> None:
    if mcp is None:
        raise ImportError("mcp package required: pip install 'datapulse[graph]'")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
