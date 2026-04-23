# Graph MCP usage — pointer

Full guide in `docs/CONVENTIONS/graph-mcp.md`.

Before editing shared code:
- `dp_context(symbol)` — callers, callees, tests, layer
- `dp_impact(symbol, max_depth=3)` — blast radius

Mandatory for: `queries.py`, `filters.py`, `cache.py`, `auth.py`/`jwt.py`/`deps.py`, any dbt model, `repository.py`/`service.py` in analytics.
