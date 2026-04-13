"""Brain database operations — lightweight psycopg2 layer.

Designed to run from the Stop hook (outside the API container), so it reads
DATABASE_URL directly from env/dotenv rather than importing Settings.
"""

from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
import psycopg2.extras

_DEFAULT_TIMEOUT = 5  # seconds
_DICT = psycopg2.extras.RealDictCursor


def _database_url() -> str | None:
    """Resolve DATABASE_URL from env, loading .env if needed."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        from dotenv import load_dotenv

        load_dotenv()
        return os.environ.get("DATABASE_URL")
    except ImportError:
        return None


def get_connection() -> psycopg2.extensions.connection:
    """Open a psycopg2 connection with a short timeout."""
    url = _database_url()
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(url, connect_timeout=_DEFAULT_TIMEOUT)


def _dict_cursor(conn: Any) -> Any:
    """Create a RealDictCursor from a connection."""
    return conn.cursor(cursor_factory=_DICT)


# ── Session operations ──────────────────────────────────────────


def insert_session(
    *,
    timestamp: str,
    branch: str,
    user_name: str,
    layers: list[str],
    modules: list[str],
    files_changed: list[str],
    commits: list[dict[str, str]],
    body_md: str,
    tenant_id: int = 1,
) -> int:
    """INSERT a session row and return the new id."""
    sql = """
        INSERT INTO brain.sessions
            (tenant_id, timestamp, branch, user_name, layers, modules,
             files_changed, commits, body_md)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            sql,
            (
                tenant_id,
                timestamp,
                branch,
                user_name,
                layers,
                modules,
                files_changed,
                json.dumps(commits),
                body_md,
            ),
        )
        row_id: int = cur.fetchone()[0]
        conn.commit()
    return row_id


def get_recent_sessions(count: int = 5) -> list[dict[str, Any]]:
    """Return the last *count* sessions, newest first."""
    sql = """
        SELECT id, timestamp, branch, user_name, layers, modules,
               files_changed, commits, body_md
        FROM brain.sessions
        ORDER BY timestamp DESC
        LIMIT %s
    """
    with get_connection() as conn, _dict_cursor(conn) as cur:
        cur.execute(sql, (count,))
        return [dict(r) for r in cur.fetchall()]


def get_session_by_id(session_id: int) -> dict[str, Any] | None:
    """Return a single session with linked decisions/incidents."""
    session_sql = """
        SELECT id, timestamp, branch, user_name, layers, modules,
               files_changed, commits, body_md
        FROM brain.sessions WHERE id = %s
    """
    decisions_sql = """
        SELECT id, title, body_md, tags, created_at
        FROM brain.decisions WHERE session_id = %s
        ORDER BY created_at
    """
    incidents_sql = """
        SELECT id, title, severity, body_md, tags, created_at
        FROM brain.incidents WHERE session_id = %s
        ORDER BY created_at
    """
    with get_connection() as conn, _dict_cursor(conn) as cur:
        cur.execute(session_sql, (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        cur.execute(decisions_sql, (session_id,))
        result["decisions"] = [dict(r) for r in cur.fetchall()]
        cur.execute(incidents_sql, (session_id,))
        result["incidents"] = [dict(r) for r in cur.fetchall()]
    return result


# ── Search operations ───────────────────────────────────────────


def search_fts(
    query: str,
    *,
    layers: list[str] | None = None,
    modules: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Full-text search across sessions, ranked by ts_rank."""
    conditions = [
        "search_vector @@ plainto_tsquery('english', %s)",
    ]
    params: list[Any] = [query]

    if layers:
        conditions.append("layers && %s")
        params.append(layers)
    if modules:
        conditions.append("modules && %s")
        params.append(modules)

    where = " AND ".join(conditions)
    params.append(limit)

    sql = f"""
        SELECT id, timestamp, branch, user_name, layers, modules,
               ts_rank(search_vector,
                       plainto_tsquery('english', %s)) AS rank
        FROM brain.sessions
        WHERE {where}
        ORDER BY rank DESC
        LIMIT %s
    """
    rank_params = [query, *params]

    with get_connection() as conn, _dict_cursor(conn) as cur:
        cur.execute(sql, rank_params)
        return [dict(r) for r in cur.fetchall()]


def search_semantic(
    query_embedding: list[float],
    *,
    layers: list[str] | None = None,
    modules: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Cosine similarity search using pgvector."""
    conditions = ["embedding IS NOT NULL"]
    params: list[Any] = []

    if layers:
        conditions.append("layers && %s")
        params.append(layers)
    if modules:
        conditions.append("modules && %s")
        params.append(modules)

    where = " AND ".join(conditions)
    vec_str = str(query_embedding)

    sql = f"""
        SELECT id, timestamp, branch, user_name, layers, modules,
               1 - (embedding <=> %s::vector) AS similarity
        FROM brain.sessions
        WHERE {where}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    params_full = [vec_str, *params, vec_str, limit]

    with get_connection() as conn, _dict_cursor(conn) as cur:
        cur.execute(sql, params_full)
        return [dict(r) for r in cur.fetchall()]


def search_hybrid(
    query: str,
    query_embedding: list[float] | None = None,
    *,
    layers: list[str] | None = None,
    modules: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Combined FTS + semantic. Falls back to FTS-only if no embedding."""
    if query_embedding is None:
        return search_fts(
            query,
            layers=layers,
            modules=modules,
            limit=limit,
        )

    conditions = [
        "search_vector @@ plainto_tsquery('english', %s)",
    ]
    params: list[Any] = [query]

    if layers:
        conditions.append("layers && %s")
        params.append(layers)
    if modules:
        conditions.append("modules && %s")
        params.append(modules)

    where = " AND ".join(conditions)
    vec_str = str(query_embedding)

    sql = f"""
        SELECT id, timestamp, branch, user_name, layers, modules,
               ts_rank(search_vector,
                       plainto_tsquery('english', %s)) AS fts_rank,
               CASE WHEN embedding IS NOT NULL
                    THEN 1 - (embedding <=> %s::vector)
                    ELSE 0
               END AS cosine_sim,
               0.4 * ts_rank(search_vector,
                             plainto_tsquery('english', %s))
               + 0.6 * CASE WHEN embedding IS NOT NULL
                            THEN 1 - (embedding <=> %s::vector)
                            ELSE 0
                       END AS combined_score
        FROM brain.sessions
        WHERE {where}
        ORDER BY combined_score DESC
        LIMIT %s
    """
    params_full = [
        query,
        vec_str,
        query,
        vec_str,
        *params,
        limit,
    ]

    with get_connection() as conn, _dict_cursor(conn) as cur:
        cur.execute(sql, params_full)
        return [dict(r) for r in cur.fetchall()]


def search_all(
    query: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Cross-table FTS search (sessions + decisions + incidents)."""
    sql = """
        (SELECT 'session' AS type, id, branch AS title,
                timestamp,
                ts_rank(search_vector,
                        plainto_tsquery('english', %s)) AS rank
         FROM brain.sessions
         WHERE search_vector @@ plainto_tsquery('english', %s))
        UNION ALL
        (SELECT 'decision' AS type, id, title,
                created_at AS timestamp,
                ts_rank(search_vector,
                        plainto_tsquery('english', %s)) AS rank
         FROM brain.decisions
         WHERE search_vector @@ plainto_tsquery('english', %s))
        UNION ALL
        (SELECT 'incident' AS type, id, title,
                created_at AS timestamp,
                ts_rank(search_vector,
                        plainto_tsquery('english', %s)) AS rank
         FROM brain.incidents
         WHERE search_vector @@ plainto_tsquery('english', %s))
        UNION ALL
        (SELECT 'knowledge' AS type, id, title,
                created_at AS timestamp,
                ts_rank(search_vector,
                        plainto_tsquery('english', %s)) AS rank
         FROM brain.knowledge
         WHERE search_vector @@ plainto_tsquery('english', %s))
        ORDER BY rank DESC
        LIMIT %s
    """
    params = (query, query, query, query, query, query, query, query, limit)

    with get_connection() as conn, _dict_cursor(conn) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


# ── Decision / Incident operations ─────────────────────────────


def insert_decision(
    *,
    title: str,
    body_md: str = "",
    tags: list[str] | None = None,
    session_id: int | None = None,
    tenant_id: int = 1,
) -> int:
    """INSERT a decision record and return the new id."""
    sql = """
        INSERT INTO brain.decisions
            (tenant_id, session_id, title, body_md, tags)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            sql,
            (
                tenant_id,
                session_id,
                title,
                body_md,
                tags or [],
            ),
        )
        row_id: int = cur.fetchone()[0]
        conn.commit()
    return row_id


def insert_incident(
    *,
    title: str,
    body_md: str = "",
    severity: str = "low",
    tags: list[str] | None = None,
    session_id: int | None = None,
    tenant_id: int = 1,
) -> int:
    """INSERT an incident record and return the new id."""
    sql = """
        INSERT INTO brain.incidents
            (tenant_id, session_id, title, severity, body_md, tags)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            sql,
            (
                tenant_id,
                session_id,
                title,
                severity,
                body_md,
                tags or [],
            ),
        )
        row_id: int = cur.fetchone()[0]
        conn.commit()
    return row_id


# ── Embedding update ────────────────────────────────────────────


# ── Knowledge operations ────────────────────────────────────────


def insert_knowledge(
    *,
    title: str,
    body_md: str = "",
    category: str = "general",
    tags: list[str] | None = None,
    tenant_id: int = 1,
) -> int:
    """INSERT a knowledge record and return the new id."""
    sql = """
        INSERT INTO brain.knowledge
            (tenant_id, category, title, body_md, tags)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (tenant_id, category, title, body_md, tags or []))
        row_id: int = cur.fetchone()[0]
        conn.commit()
    return row_id


def search_knowledge(
    query: str,
    *,
    category: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """FTS search across brain.knowledge, optionally filtered by category."""
    conditions = ["search_vector @@ plainto_tsquery('english', %s)"]
    params: list[Any] = [query]

    if category:
        conditions.append("category = %s")
        params.append(category)

    where = " AND ".join(conditions)
    params.append(limit)

    sql = f"""
        SELECT id, category, title, body_md, tags, created_at, updated_at,
               ts_rank(search_vector, plainto_tsquery('english', %s)) AS rank
        FROM brain.knowledge
        WHERE {where}
        ORDER BY rank DESC
        LIMIT %s
    """
    rank_params = [query, *params]

    with get_connection() as conn, _dict_cursor(conn) as cur:
        cur.execute(sql, rank_params)
        return [dict(r) for r in cur.fetchall()]


# ── Embedding update ────────────────────────────────────────────


def update_embedding(
    table: str,
    row_id: int,
    embedding: list[float],
) -> None:
    """Set the embedding column for a given row."""
    if table not in ("sessions", "decisions", "incidents", "knowledge"):
        raise ValueError(f"Invalid table: {table}")
    sql = f"UPDATE brain.{table} SET embedding = %s::vector WHERE id = %s"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (str(embedding), row_id))
        conn.commit()
