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

__all__ = ["build_set_eq", "build_where", "build_where_eq"]


# Operators accepted by build_where(). Anything outside this set is a call-site
# bug — raise rather than splice unknown operator text into SQL.
_ALLOWED_OPERATORS = frozenset({"=", "!=", "<>", "<", "<=", ">", ">="})


def build_where(
    conditions: list[tuple[str, str, str, Any]],
    *,
    extra_clauses: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build a parameterized WHERE body from comparison conditions.

    Each condition is a 4-tuple ``(column_expr, operator, param_name, value)``:
    - ``column_expr`` — the SQL side (e.g. ``"m.movement_date"``). Always a
      literal at the call site, never user input.
    - ``operator`` — one of ``=``, ``!=``, ``<>``, ``<``, ``<=``, ``>``, ``>=``.
      Any other value raises ``ValueError`` (defensive: we never splice unknown
      operator text into SQL).
    - ``param_name`` — bind-parameter name; appears as ``:<param_name>`` in SQL.
    - ``value`` — Python value. If ``None``, the clause is dropped.

    Example:
        clause, params = build_where([
            ("m.site_key",       "=",  "site_key",   filters.site_key),
            ("m.movement_date",  ">=", "start_date", filters.start_date),
            ("m.movement_date",  "<=", "end_date",   filters.end_date),
        ])

    See :func:`build_where_eq` for an equality-only shortcut that skips the
    operator column in each tuple.
    """
    fragments: list[str] = []
    params: dict[str, Any] = {}

    for column_expr, operator, param_name, value in conditions:
        if operator not in _ALLOWED_OPERATORS:
            raise ValueError(f"build_where: unsupported operator {operator!r}")
        if value is None:
            continue
        fragments.append(f"{column_expr} {operator} :{param_name}")
        params[param_name] = value

    if extra_clauses:
        fragments.extend(extra_clauses)

    clause = " AND ".join(fragments) if fragments else "1=1"
    return clause, params


def build_where_eq(
    conditions: list[tuple[str, str, Any]],
    *,
    extra_clauses: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Equality-only shortcut for :func:`build_where`.

    Each condition is a 3-tuple ``(column_expr, param_name, value)``. The
    operator is always ``=``. ``None`` values are dropped.

    Example:
        clause, params = build_where_eq([
            ("po.tenant_id",     "tenant_id",     tenant_id),
            ("po.status",        "status",        status),
            ("po.supplier_code", "supplier_code", supplier_code),
        ])
    """
    return build_where(
        [(col, "=", name, value) for col, name, value in conditions],
        extra_clauses=extra_clauses,
    )


def build_set_eq(
    assignments: list[tuple[str, str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Build a parameterized SET body for UPDATE statements.

    Each assignment is a 3-tuple ``(column_name, param_name, value)``. Values
    that are ``None`` are dropped, which maps naturally to "only update the
    columns the caller supplied."

    Returns ``(set_body, params)``. ``set_body`` is the body of a SET clause
    (no leading ``SET``). When *no* assignment survives, returns an empty
    string — callers must handle the "nothing to update" case explicitly,
    since issuing ``UPDATE ... SET  WHERE ...`` would be a syntax error.

    Example:
        body, params = build_set_eq([
            ("role_id",      "rid",    role["role_id"]),
            ("display_name", "name",   new_name),
            ("is_active",    "active", is_active),
        ])
        if not body:
            return self.get_member_by_id(member_id)
        session.execute(
            text(f"UPDATE tenant_members SET {body} WHERE member_id = :mid"),
            {"mid": member_id, **params},
        )
    """
    fragments: list[str] = []
    params: dict[str, Any] = {}
    for column_name, param_name, value in assignments:
        if value is None:
            continue
        fragments.append(f"{column_name} = :{param_name}")
        params[param_name] = value
    return ", ".join(fragments), params
