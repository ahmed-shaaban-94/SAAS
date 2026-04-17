"""Canonical domain registry helpers.

The canonical_domains table (migration 042) is the single source of truth
for semantic schemas. This module provides read helpers used by validation
and route layers.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


def list_canonical_domains(session: Session) -> list[dict[str, Any]]:
    """Return all active canonical domains as plain dicts."""
    stmt = text("""
        SELECT domain_key, version, display_name, description,
               json_schema, is_active
        FROM public.canonical_domains
        WHERE is_active = TRUE
        ORDER BY domain_key
    """)
    rows = session.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_canonical_domain(session: Session, domain_key: str) -> dict[str, Any] | None:
    """Return one canonical domain by key, or None if missing / inactive."""
    stmt = text("""
        SELECT domain_key, version, display_name, description,
               json_schema, is_active
        FROM public.canonical_domains
        WHERE domain_key = :key AND is_active = TRUE
    """)
    row = session.execute(stmt, {"key": domain_key}).mappings().fetchone()
    if row is None:
        return None
    return dict(row)


def required_fields_for(schema: dict[str, Any]) -> list[str]:
    """Extract required_fields array from a canonical json_schema."""
    fields = schema.get("required_fields", [])
    if not isinstance(fields, list):
        log.warning("canonical_schema_invalid_required_fields", fields=fields)
        return []
    return [str(f) for f in fields]


def field_types_for(schema: dict[str, Any]) -> dict[str, str]:
    """Extract {field: type} map from a canonical json_schema."""
    types = schema.get("types", {})
    if not isinstance(types, dict):
        log.warning("canonical_schema_invalid_types", types=types)
        return {}
    return {str(k): str(v) for k, v in types.items()}
