"""Nightly RLS enforcement audit for marts and staging schemas.

dbt creates tables before applying ``FORCE ROW LEVEL SECURITY`` in
post-hooks. If a dbt run crashes between creation and post-hook, the
table briefly exists without RLS and the DB owner role can read
cross-tenant data (#546). This module is the safety net: a scheduled
check that every table in ``public_marts`` and ``public_staging`` has
both ``relrowsecurity`` AND ``relforcerowsecurity`` set.

The Slack alerter lives in :mod:`datapulse.notifications`; the APScheduler
wrapper lives in :mod:`datapulse.scheduler.triggers`. Keeping the auditor
pure (session in, list out) lets it be tested without mocking a scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

AUDITED_SCHEMAS: tuple[str, ...] = ("public_marts", "public_staging")

_AUDIT_QUERY = text(
    """
    SELECT n.nspname AS schema_name,
           c.relname AS table_name,
           c.relrowsecurity AS row_security,
           c.relforcerowsecurity AS force_row_security
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = ANY(:schemas)
      AND c.relkind = 'r'
      AND NOT (c.relrowsecurity AND c.relforcerowsecurity)
    ORDER BY n.nspname, c.relname
    """
)


@dataclass(frozen=True)
class RlsViolation:
    """A table that failed the RLS+FORCE invariant."""

    schema: str
    table: str
    row_security: bool
    force_row_security: bool

    @property
    def fqn(self) -> str:
        return f"{self.schema}.{self.table}"


def audit_rls_enforcement(
    session: Session,
    schemas: tuple[str, ...] = AUDITED_SCHEMAS,
) -> list[RlsViolation]:
    """Return every table in ``schemas`` that is missing RLS or FORCE RLS.

    An empty list means the invariant holds. The caller decides how to
    react (log, alert, fail a health probe).
    """
    rows = session.execute(_AUDIT_QUERY, {"schemas": list(schemas)}).all()
    return [
        RlsViolation(
            schema=row.schema_name,
            table=row.table_name,
            row_security=bool(row.row_security),
            force_row_security=bool(row.force_row_security),
        )
        for row in rows
    ]
