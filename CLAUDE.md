# DataPulse

Data analytics SaaS: Excel/CSV → medallion (bronze/silver/gold) → FastAPI + Next.js → Power BI.

## Session start
Read `docs/brain/_INDEX.md` for recent session context.

## Long-form references — load only when relevant

- `docs/CLAUDE_REFERENCE.md` — tech stack, directory tree, Docker, schemas, team roles, agents, phase roadmap
- `docs/ARCHITECTURE.md` — Mermaid diagrams, data flow, request flow, ERD, deployment
- `docs/RUNBOOK.md` — ops procedures
- `docs/CONVENTIONS/layer-boundaries.md` — module dependency graph (enforced)
- `docs/CONVENTIONS/graph-mcp.md` — `dp_context` / `dp_impact` / `dp_query` usage
- `docs/CONVENTIONS/second-brain.md` — brain vault reads + writes
- `.claude/rules/*.md` — thin pointers to the above

## Hard rules (always in force)

### Security
- Tenant-scoped RLS on `bronze.sales`, all marts, agg tables, and silver view; `FORCE ROW LEVEL SECURITY` on all; silver uses `security_invoker=on`
- Session pattern: `SET LOCAL app.tenant_id = '<id>'` derived from JWT `tenant_id` claim
- Financial columns: `NUMERIC(18,4)` — never float
- SQL column whitelist before INSERT (injection prevention)
- Credentials in `.env` only — never hardcoded
- Docker ports bound to `127.0.0.1`
- Auth: Clerk is the sole IdP; backend JWT verifies `tenant_id` + `roles` claims from the `datapulse` JWT template
- CORS restricted headers (Content-Type, Authorization, X-API-Key, X-Pipeline-Token); rate limit 60/min analytics, 5/min pipeline mutations
- Health endpoint returns 503 when DB unreachable (not 200)

### Python
- 3.11+, ruff line-length=100
- Pydantic models for all config + data contracts
- Type hints on all public functions
- Immutable — create new objects, never mutate
- Small files (200–400 lines typical, 800 max); functions <50 lines; nesting <4
- `structlog` for structured JSON logging
- `JsonDecimal` type alias: Decimal precision internally, float serialization in JSON

### Git / workflow
- Each feature = separate branch (descriptive name)
- Commit: `<type>: <description>` (feat / fix / refactor / docs / test / chore / perf / ci)
- Before push (mandatory): `ruff format --check src/ tests/`, `ruff check src/ tests/`, `pytest -m unit -x -q`
- After changing a function signature: `grep -rn "assert_called.*func_name" tests/` to catch stale mock assertions
- 80%+ coverage target on new code (unit gate enforced at 77% in CI)

### Data pipeline
- Verify referenced columns exist in source before adding dbt transforms
- Bronze loader: `docker exec -it datapulse-api python -m datapulse.bronze.loader --source /app/data/raw/sales`

### Docs language
- Code + docs: English
- Inline comments: Arabic allowed where it aids clarity
