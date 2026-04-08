"""SQLite-backed graph store for DataPulse code intelligence.

Stores symbols (functions, classes, components, dbt models) and edges
(calls, imports, depends_on) in a lightweight local database.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path.home() / ".datapulse" / "graph.db"


def _ensure_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _connect():
    _ensure_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS symbols (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                kind        TEXT    NOT NULL,
                file_path   TEXT    NOT NULL,
                line_number INTEGER DEFAULT 0,
                module      TEXT,
                layer       TEXT,
                extra       TEXT,
                UNIQUE(name, kind, file_path, line_number)
            );

            CREATE TABLE IF NOT EXISTS edges (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
                target_id INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
                kind      TEXT    NOT NULL,
                UNIQUE(source_id, target_id, kind)
            );

            CREATE INDEX IF NOT EXISTS idx_symbols_name  ON symbols(name);
            CREATE INDEX IF NOT EXISTS idx_symbols_layer ON symbols(layer);
            CREATE INDEX IF NOT EXISTS idx_symbols_kind  ON symbols(kind);
            CREATE INDEX IF NOT EXISTS idx_symbols_file  ON symbols(file_path);
            CREATE INDEX IF NOT EXISTS idx_edges_source  ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target  ON edges(target_id);
        """)


def clear() -> None:
    """Drop all data (used before re-indexing)."""
    with _connect() as conn:
        conn.execute("DELETE FROM edges")
        conn.execute("DELETE FROM symbols")


def upsert_symbol(
    name: str,
    kind: str,
    file_path: str,
    line_number: int = 0,
    module: str | None = None,
    layer: str | None = None,
    extra: str | None = None,
) -> int:
    """Insert or ignore a symbol, return its id."""
    with _connect() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO symbols
               (name, kind, file_path, line_number, module, layer, extra)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, kind, file_path, line_number, module, layer, extra),
        )
        row = conn.execute(
            "SELECT id FROM symbols WHERE name=? AND kind=? AND file_path=? AND line_number=?",
            (name, kind, file_path, line_number),
        ).fetchone()
        return row["id"]


def add_edge(source_id: int, target_id: int, kind: str) -> None:
    """Add a directed edge between two symbols."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO edges (source_id, target_id, kind) VALUES (?, ?, ?)",
            (source_id, target_id, kind),
        )


def find_symbol(name: str, kind: str | None = None) -> list[dict]:
    """Find symbols by name (exact or LIKE)."""
    with _connect() as conn:
        if kind:
            rows = conn.execute(
                "SELECT * FROM symbols WHERE name LIKE ? AND kind = ?",
                (f"%{name}%", kind),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM symbols WHERE name LIKE ?", (f"%{name}%",)
            ).fetchall()
        return [dict(r) for r in rows]


def find_by_file(file_path: str) -> list[dict]:
    """Find all symbols defined in a specific file."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM symbols WHERE file_path = ?", (file_path,)).fetchall()
        return [dict(r) for r in rows]


def get_symbol_by_id(sid: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM symbols WHERE id=?", (sid,)).fetchone()
        return dict(row) if row else None


def get_edges_from(sid: int) -> list[dict]:
    """Outgoing edges (this symbol → others)."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT e.kind, s.name, s.kind as sym_kind, s.file_path, s.line_number, s.layer
               FROM edges e JOIN symbols s ON e.target_id = s.id
               WHERE e.source_id = ?""",
            (sid,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_edges_to(sid: int) -> list[dict]:
    """Incoming edges (others → this symbol)."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT e.kind, s.name, s.kind as sym_kind, s.file_path, s.line_number, s.layer
               FROM edges e JOIN symbols s ON e.source_id = s.id
               WHERE e.target_id = ?""",
            (sid,),
        ).fetchall()
        return [dict(r) for r in rows]


def impact_query(symbol_name: str, max_depth: int = 3) -> dict[int, list[dict]]:
    """BFS from a symbol outward through edges, grouped by depth."""
    seeds = find_symbol(symbol_name)
    if not seeds:
        return {}

    visited: set[int] = set()
    result: dict[int, list[dict]] = {}
    frontier = [s["id"] for s in seeds]
    visited.update(frontier)

    for depth in range(1, max_depth + 1):
        next_frontier: list[int] = []
        depth_hits: list[dict] = []
        for sid in frontier:
            for edge in get_edges_to(sid):
                target = find_symbol(edge["name"], edge["sym_kind"])
                for t in target:
                    if t["id"] not in visited:
                        visited.add(t["id"])
                        next_frontier.append(t["id"])
                        depth_hits.append(
                            {
                                "name": edge["name"],
                                "kind": edge["sym_kind"],
                                "file": edge["file_path"],
                                "line": edge["line_number"],
                                "layer": edge["layer"],
                                "relationship": edge["kind"],
                                "depth": depth,
                            }
                        )
            for edge in get_edges_from(sid):
                target = find_symbol(edge["name"], edge["sym_kind"])
                for t in target:
                    if t["id"] not in visited:
                        visited.add(t["id"])
                        next_frontier.append(t["id"])
                        depth_hits.append(
                            {
                                "name": edge["name"],
                                "kind": edge["sym_kind"],
                                "file": edge["file_path"],
                                "line": edge["line_number"],
                                "layer": edge["layer"],
                                "relationship": edge["kind"],
                                "depth": depth,
                            }
                        )
        if depth_hits:
            result[depth] = depth_hits
        frontier = next_frontier
        if not frontier:
            break
    return result


def context_query(symbol_name: str) -> dict[str, Any]:
    """360-degree view: callers, callees, references, tests, layer info."""
    symbols = find_symbol(symbol_name)
    if not symbols:
        return {"error": f"Symbol '{symbol_name}' not found"}

    sym = symbols[0]
    outgoing = get_edges_from(sym["id"])
    incoming = get_edges_to(sym["id"])

    callers = [e for e in incoming if e["kind"] == "calls"]
    callees = [e for e in outgoing if e["kind"] == "calls"]
    imports = [e for e in incoming if e["kind"] == "imports"]
    depends = [e for e in outgoing if e["kind"] == "depends_on"]
    tests = [e for e in incoming if e["kind"] == "tests"]
    references = [e for e in incoming if e["kind"] == "references"]

    return {
        "symbol": sym["name"],
        "kind": sym["kind"],
        "defined_in": f"{sym['file_path']}:{sym['line_number']}",
        "layer": sym["layer"],
        "module": sym["module"],
        "callers": [_fmt(e) for e in callers],
        "callees": [_fmt(e) for e in callees],
        "imported_by": [_fmt(e) for e in imports],
        "depends_on": [_fmt(e) for e in depends],
        "tested_by": [_fmt(e) for e in tests],
        "referenced_by": [_fmt(e) for e in references],
    }


def search_query(query: str, kind: str | None = None, layer: str | None = None) -> list[dict]:
    """Search symbols with optional filters."""
    with _connect() as conn:
        sql = "SELECT * FROM symbols WHERE name LIKE ?"
        params: list[Any] = [f"%{query}%"]
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        if layer:
            sql += " AND layer = ?"
            params.append(layer)
        sql += " ORDER BY name LIMIT 50"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def stats() -> dict:
    """Return index statistics."""
    with _connect() as conn:
        sym_count = conn.execute("SELECT COUNT(*) c FROM symbols").fetchone()["c"]
        edge_count = conn.execute("SELECT COUNT(*) c FROM edges").fetchone()["c"]
        layers = conn.execute(
            "SELECT layer, COUNT(*) c FROM symbols GROUP BY layer ORDER BY c DESC"
        ).fetchall()
        kinds = conn.execute(
            "SELECT kind, COUNT(*) c FROM symbols GROUP BY kind ORDER BY c DESC"
        ).fetchall()
        return {
            "total_symbols": sym_count,
            "total_edges": edge_count,
            "by_layer": {r["layer"] or "unknown": r["c"] for r in layers},
            "by_kind": {r["kind"]: r["c"] for r in kinds},
        }


def _fmt(edge: dict) -> str:
    return f"{edge['file_path']}:{edge['line_number']} → {edge['name']}()"
