"""DataPulse Graph MCP Server — 4 tools for Claude Code integration.

Tools:
    dp_impact   — Blast radius: what breaks if I change X?
    dp_context  — 360° view of any symbol
    dp_query    — Search the code graph
    dp_detect_changes — Map git diff to affected symbols

Usage:
    python -m datapulse.graph.mcp_server
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from datapulse.graph import store
from datapulse.graph.indexer import index

mcp = FastMCP("datapulse-graph")

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
