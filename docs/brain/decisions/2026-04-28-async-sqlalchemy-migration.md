# Async SQLAlchemy + asyncpg migration — decision record

**Date:** 2026-04-28
**Branch of record:** fix/clerk-routing-env
**Status:** in progress — leads + health migrated; ~115 files remain

## Why

- Sync psycopg2 + threaded workers caps p99 latency under bursty load: every
  request holds a worker thread for the full DB round-trip.
- asyncpg is the fastest Postgres driver for Python and frees the event
  loop during waits, so a single UvicornWorker can serve far more
  concurrent slow analytics queries.
- SQLAlchemy 2.0 async is mature; we already pin `sqlalchemy>=2.0,<3`.

## Coexistence strategy

- `get_engine` (sync) and `get_async_engine` (async) live side-by-side in
  `src/datapulse/core/db.py`. Same for session factories.
- `get_tenant_session` (sync) and `get_tenant_session_async` (async) live
  side-by-side in `src/datapulse/core/auth.py`.
- Each repository / route migrates in its own PR. Until a repo is migrated
  it keeps `Depends(get_tenant_session)` and a sync `Session`.

## Mechanical recipe per repository

1. `Session` → `AsyncSession` in the type hint.
2. Each method becomes `async def`.
3. `session.execute(...)` → `await session.execute(...)`.
4. `session.scalar(...)` / `session.scalars(...)` → `await session.scalar(...)` / `await session.scalars(...)`.
5. `session.flush()` → `await session.flush()`.
6. `session.refresh(obj)` → `await session.refresh(obj)`.
7. `session.commit()` → DELETE — commit happens in the dep teardown.
8. `session.add(...)` and `Result.scalars()` / `.all()` / `.first()` stay sync.
9. Service: every method that awaits the repo becomes `async def` + `await`.
10. Factory in `api/deps.py`: `Depends(get_tenant_session)` → `Depends(get_tenant_session_async)`.
11. Route handler: `def` → `async def`, prefix `service.method(...)` calls with `await`.

## PgBouncer note

`statement_cache_size=0` is mandatory in `connect_args` for asyncpg under
PgBouncer transaction-pooling mode. Encoded in `get_async_engine`.

## sslmode note

asyncpg ignores `?sslmode=` in the URL. If TLS enforcement is needed,
pass `connect_args={"ssl": True}` to `create_async_engine`. The sync
`_validate_database_url` check is run on the original URL before rewrite;
translate sslmode=require before shipping to a TLS-enforced prod cluster
(see TODO comment in `src/datapulse/core/db.py`).

## Out of scope this PR

- Read-replica async path (`get_tenant_session_readonly`). Stays sync.
- `tenant_session()` sync context manager used by scheduler / bronze /
  control_center — those are background jobs, not request-path.
- `src/datapulse/brain/db.py` and `graph/mcp_server.py` — separate engines.

## Rollback

The sync stack is untouched. Reverting any single migration PR rolls that
slice back without affecting others.
