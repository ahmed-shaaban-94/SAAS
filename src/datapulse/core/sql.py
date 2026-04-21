"""SQL helpers usable by any business module.

Lives in ``core`` so every business layer (analytics, pipeline, purchase_orders,
inventory, etc.) can import it without violating the module-dependency rules
(business layers may import from ``core`` but never from ``api``).

Prefer these helpers over hand-rolled f-string WHERE builders: they keep every
clause a *hardcoded string literal* at the call site, with user values flowing
only through bound parameters. This makes it structurally impossible to
accidentally interpolate untrusted input into SQL.
"""

from __future__ import annotations

from typing import Any

__all__ = ["build_where_eq"]


def build_where_eq(
    conditions: list[tuple[str, str, Any]],
    *,
    extra_clauses: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build a parameterized WHERE body from equality conditions.

    Each condition is a 3-tuple ``(column_expr, param_name, value)``:
    - ``column_expr`` — the SQL side (e.g. ``"po.status"``). Always a literal
      at the call site, never user input.
    - ``param_name`` — the bind-parameter name (e.g. ``"status"``). Appears as
      ``:<param_name>`` in the emitted SQL.
    - ``value`` — the Python value. If ``None``, the clause is dropped.

    Example:
        clause, params = build_where_eq([
            ("po.tenant_id",     "tenant_id",     tenant_id),
            ("po.status",        "status",        status),
            ("po.supplier_code", "supplier_code", supplier_code),
        ])
        # → ("po.tenant_id = :tenant_id AND po.status = :status", {...})
        # if supplier_code was None, its clause is dropped.

    Args:
        conditions: Equality clauses. ``None`` values are filtered out.
        extra_clauses: Additional SQL fragments that do not need bind params
            (e.g. ``"po.is_deleted = FALSE"``). Appended with AND. Must also
            be literals at the call site.

    Returns:
        ``(clause, params)``. ``clause`` is the body of a WHERE (no leading
        ``WHERE``); ``params`` is a dict ready to pass to SQLAlchemy ``text()``
        execution. When no clause survives, ``clause`` is ``"1=1"`` so the
        caller can interpolate it safely after ``WHERE``.
    """
    fragments: list[str] = []
    params: dict[str, Any] = {}

    for column_expr, param_name, value in conditions:
        if value is None:
            continue
        fragments.append(f"{column_expr} = :{param_name}")
        params[param_name] = value

    if extra_clauses:
        fragments.extend(extra_clauses)

    clause = " AND ".join(fragments) if fragments else "1=1"
    return clause, params
