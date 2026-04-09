# ADR-003: Row Level Security for multi-tenant isolation

**Status**: Accepted  
**Date**: 2026-04-09  
**Deciders**: Platform Engineer, Pipeline Engineer

## Context

DataPulse is a multi-tenant SaaS. Multiple pharmacy chains (tenants) share the same PostgreSQL database. Tenant data must be completely isolated — a query from Tenant A must never return Tenant B's data, even if the application has a bug.

Application-level filtering (`WHERE tenant_id = ?`) is not sufficient because:
- A single missing WHERE clause in any query leaks cross-tenant data
- Query builder bugs, SQL injection, or copy-paste errors can silently bypass it
- There is no defense-in-depth

## Decision

Use **PostgreSQL Row Level Security (RLS)** as the primary isolation mechanism:

1. **Policy pattern**: All tenant-scoped tables use:
   ```sql
   USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
   ```
   The `NULLIF(..., '')::INT` pattern handles NULL/empty gracefully (returns NULL which matches no rows).

2. **Session variable**: Each API request sets `SET LOCAL app.tenant_id = '<id>'` derived from the JWT `tenant_id` claim. This is local to the transaction — it cannot bleed across requests.

3. **FORCE ROW LEVEL SECURITY**: Applied to all RLS-enabled tables. This prevents the table owner (datapulse user) from bypassing RLS, avoiding a privilege escalation vector.

4. **datapulse_reader role**: A read-only role used by analytics queries. It connects with RLS enforced — no `BYPASSRLS` privilege.

5. **dbt post_hooks**: Every mart table's dbt model includes a `post-hook` to enable RLS, grant to `datapulse_reader`, and create the policy. This ensures RLS is always in sync with schema changes.

## Consequences

**Good:**
- Cross-tenant data leaks require breaking PostgreSQL itself, not just the application
- New tables that add RLS via the standard template get isolation automatically
- `datapulse_reader` role enforces read-only access at the DB level

**Risks/trade-offs:**
- `SET LOCAL` must be called before every query in a session — missed in batch jobs means queries silently return 0 rows (safer than leaking, but confusing to debug)
- RLS adds a policy check overhead per row (~5-10% on large scans, negligible on indexed lookups)
- The `current_setting('app.tenant_id', true)::INT` cast fails with `invalid input syntax` if tenant_id is non-numeric — handled by `NULLIF` returning NULL
