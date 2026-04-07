"""Sector-based data filtering for analytics queries.

Provides SQL WHERE clause fragments that restrict data access
based on the user's sector assignments. Owners and admins
bypass filtering (see all data).
"""

from __future__ import annotations

from datapulse.rbac.models import AccessContext


def build_sector_filter(
    ctx: AccessContext,
    site_column: str = "site",
    param_prefix: str = "sector",
) -> tuple[str, dict]:
    """Build a SQL WHERE clause fragment for sector filtering.

    Returns (sql_fragment, params) where:
    - sql_fragment is empty string if user has full access
    - sql_fragment is "AND site IN :sector_sites" otherwise
    - params contains the bind parameters

    Args:
        ctx: The user's resolved access context.
        site_column: The SQL column name for site (e.g., "s.site", "site").
        param_prefix: Prefix for bind parameter names (to avoid collisions).

    Returns:
        (where_clause, params) tuple. Append where_clause to your SQL.
    """
    if ctx.has_full_access:
        return "", {}

    if not ctx.site_codes:
        # User has no sectors assigned — show no data
        return f"AND {site_column} IS NULL AND FALSE", {}

    param_name = f"{param_prefix}_sites"
    return f"AND {site_column} = ANY(:{param_name})", {param_name: ctx.site_codes}


def get_accessible_site_codes(ctx: AccessContext) -> list[str] | None:
    """Return site codes the user can access, or None for full access.

    None means "no restriction" (owner/admin).
    Empty list means "no access to any site".
    """
    if ctx.has_full_access:
        return None
    return ctx.site_codes
