# Design: Project Simplification Sprint + Brain → Obsidian Export

- **Date:** 2026-04-15
- **Branch:** `claude/zen-einstein`
- **Author:** Ahmed Shaaban (with Claude)
- **Status:** Approved — ready for implementation planning

---

## 1. Summary

Two sequential, independently-shippable initiatives:

1. **Phase 1 — Simplification Sprint**: reduce project-wide noise by splitting oversized Python files into cohesive modules and consolidating duplicated helpers. No behavior changes. One bundled PR.
2. **Phase 2 — Brain → Obsidian Export** *(after Phase 1 merges)*: add a CLI that pulls the droplet's `brain.*` PostgreSQL tables and writes an Obsidian-compatible markdown vault under `docs/brain/vault/`, with `[[wikilinks]]` so Obsidian's graph view renders real session ↔ layer ↔ module ↔ decision ↔ incident relationships. No database schema change.

Shared motivation: a codebase we can read at a glance, and a second brain we can *see*.

---

## 2. Motivation & Current State

### 2.1 Noise inventory (why Phase 1 is needed)

Ran `wc -l` across `src/datapulse/` (~34,100 LOC total) and queried the `datapulse-graph` MCP. Findings:

**Files exceeding CLAUDE.md's 800-LOC cap:**

| File | LOC | Problem |
|------|-----|---------|
| `src/datapulse/control_center/repository.py` | 937 | 7 separate Repository classes stuffed into one module |
| `src/datapulse/api/routes/control_center.py` | 912 | 7 resource routers in one file |
| `src/datapulse/control_center/service.py` | 865 | Single 800-line `ControlCenterService` mixing connector types |
| `src/datapulse/analytics/kpi_repository.py` | 778 | At the cap, multiple KPI families in one class |
| `src/datapulse/analytics/models.py` | 675 | 47 Pydantic classes in one file |
| `src/datapulse/api/routes/analytics.py` | 657 | All analytics endpoints in one router |
| `src/datapulse/analytics/service.py` | 651 | Orchestration for all analytics repositories |
| `src/datapulse/scheduler.py` | 646 | Executor + trigger registry + job models fused |

**Duplicated helpers (graph-confirmed):**

- `_set_cache` is defined 7 times across `api/routes/{analytics,anomalies,branding,forecasting,gamification,reseller,targets}.py` — identical copy-paste.

**What is *not* noise** (leave alone):

- `analytics/` already has 18 focused repository-style files; that split is sound.
- No `TODO`/`FIXME`/`HACK`/`XXX` markers anywhere in `src/` — no latent debt comments to chase.
- No unused imports flagged by current ruff baseline.

### 2.2 Brain schema today (why Phase 2 is needed)

Current `brain` schema (migrations 039, 040):

```
brain.sessions   (id, timestamp, branch, user_name, layers[], modules[],
                  files_changed[], commits JSONB, body_md, search_vector, embedding)
brain.decisions  (id, session_id FK, title, body_md, tags[], ...)
brain.incidents  (id, session_id FK, title, severity, body_md, tags[], ...)
brain.knowledge  (id, category, title, body_md, tags[], ...)
```

This is a **document store with FTS + pgvector**, not a graph. Relationships exist only as:
- `TEXT[]` arrays (`layers`, `modules`, `tags`) — not first-class entities.
- One-level FKs (decisions/incidents → sessions).

The local vault (`docs/brain/`) has empty placeholder directories (`layers/_README.md`, `modules/_README.md`, `roles/_README.md`) but no generated pages for Obsidian's graph view to link to. The Stop hook writes session markdown files locally but does not materialize node pages.

**Insight that shapes the design:** Obsidian's graph view works entirely from `[[wikilinks]]` in markdown files. It does not need an edges table. The cheapest path to a working visualization is *rendering* the existing `brain.*` tables as markdown with wikilinks — no schema migration required.

---

## 3. Phase 1 — Simplification Sprint

### 3.1 Goals

- Every Python file in `src/datapulse/` < 400 LOC (CLAUDE.md's typical target), with 800 as a hard cap.
- Every duplicated helper consolidated into exactly one implementation.
- Zero behavior changes. Zero schema changes. Zero new dependencies.
- Test suite remains green. Coverage remains ≥ 95%.

### 3.2 File splits

Each split follows the same pattern: **one concept per file**, barrel `__init__.py` re-exports for backwards-compatible imports where needed.

#### 3.2.1 `control_center/repository.py` (937 → 7 files)

```
src/datapulse/control_center/repositories/
├── __init__.py                      # re-exports all 7 classes
├── source_connection.py             # SourceConnectionRepository
├── pipeline_profile.py              # PipelineProfileRepository
├── mapping_template.py              # MappingTemplateRepository
├── pipeline_draft.py                # PipelineDraftRepository
├── pipeline_release.py              # PipelineReleaseRepository
├── sync_job.py                      # SyncJobRepository
└── sync_schedule.py                 # SyncScheduleRepository
```

Shared private helpers stay in `control_center/_sql.py` if any exist after the split.

#### 3.2.2 `control_center/service.py` (865 → split by connector)

Inspect `ControlCenterService` for natural seams (likely per-connector methods + orchestration). Target layout:

```
src/datapulse/control_center/
├── service.py                        # thin facade: ControlCenterService
├── connectors.py                     # _get_connector dispatcher
└── services/
    ├── __init__.py
    ├── sources.py                    # connection CRUD + test
    ├── pipelines.py                  # profile/draft/release lifecycle
    ├── mappings.py                   # column mapping templates
    └── sync.py                       # job execution + scheduling
```

#### 3.2.3 `api/routes/control_center.py` (912 → split by resource)

```
src/datapulse/api/routes/control_center/
├── __init__.py                       # router = APIRouter(), includes sub-routers
├── sources.py
├── pipelines.py                      # covers profiles + drafts + releases
├── mappings.py
├── jobs.py
└── schedules.py
```

The existing FastAPI path prefix stays identical; only the internal composition changes.

#### 3.2.4 `analytics/models.py` (675 → 6 domain files)

```
src/datapulse/analytics/models/
├── __init__.py                       # re-export for backwards compatibility
├── kpi.py                            # revenue/transaction/margin summaries
├── ranking.py                        # top-N products/customers/staff
├── breakdown.py                      # by_period, by_category, by_channel
├── detail.py                         # single-entity detail responses
├── churn.py                          # churn + risk distribution models
└── health.py                         # customer_health / cohort models
```

Grouping mirrors existing repository file names — maps cleanly.

#### 3.2.5 `api/routes/analytics.py` (657 → split by family)

Group endpoints by the same 6 domains as the models. Each sub-router <150 LOC.

#### 3.2.6 `analytics/service.py` (651 → split by domain)

Follow the same 6-domain split. Thin `AnalyticsService` facade preserved so route-level imports don't churn.

#### 3.2.7 `analytics/kpi_repository.py` (778 → extract subclasses)

Inspect class for natural KPI families (revenue/transaction/margin/target). Extract each into its own file if the class has separable concerns, otherwise leave and note.

#### 3.2.8 `scheduler.py` (646 → 3 files)

```
src/datapulse/scheduler/
├── __init__.py                       # public API re-exports
├── executor.py                       # job execution loop
├── triggers.py                       # cron / interval / event trigger registry
└── models.py                         # Job, Schedule, Trigger dataclasses
```

### 3.3 Duplicated-helper consolidation

**`_set_cache` (7 copies → 1):**

New file: `src/datapulse/api/cache_utils.py`

```python
"""Shared cache primitives used across route modules."""
from collections.abc import Callable
from typing import Any

from datapulse.cache_decorator import cache_get, cache_set  # whatever the current names are


def set_cached(key: str, value: Any, ttl: int | None = None) -> None:
    """Single source of truth. Replaces per-route _set_cache copies."""
    cache_set(key, value, ttl=ttl)
```

Then in each of the 7 route files: `from datapulse.api.cache_utils import set_cached as _set_cache` (preserve the underscore-prefix alias so callers don't change), or directly refactor callers to `set_cached(...)` — whichever is smaller diff.

If other near-duplicates emerge during the split (likely: similar `_hash_params`, error-handler decorators, tenant-context helpers), add them to `cache_utils.py` or a new `api/_helpers.py` in the same PR.

### 3.4 Quality gates (must pass before PR)

- `ruff format --check src/ tests/` → clean
- `ruff check src/ tests/` → clean
- `pytest -x -q --cov=src/datapulse --cov-fail-under=95` → green
- `mypy src/datapulse/` → no new errors vs. baseline (record baseline in PR description)
- Full `docker compose up` smoke test: API starts, one analytics endpoint returns 200, frontend loads.

### 3.5 Out of scope for Phase 1

- Security review of fixes (separate future pass if requested).
- Performance profiling.
- New tests beyond maintaining coverage.
- Frontend changes.
- Dependency upgrades.

---

## 4. Phase 2 — Brain → Obsidian Export

### 4.1 Goals

- One command (`python -m datapulse.brain.export`) pulls the droplet's `brain.*` tables and generates a self-contained Obsidian vault at `docs/brain/vault/`.
- The vault's graph view shows real session ↔ layer ↔ module ↔ decision ↔ incident connections.
- No PostgreSQL schema change. No migrations. Works against the existing production brain DB on the droplet.

### 4.2 Architecture

```
           ┌─────────────────────────────┐
 droplet ─►│  PostgreSQL 16 + pgvector    │
  :5432    │  brain.sessions              │
           │  brain.decisions             │
           │  brain.incidents             │
           │  brain.knowledge             │
           └───────────────┬─────────────┘
                           │ psycopg2 (existing get_connection)
                           ▼
           ┌─────────────────────────────┐
           │  datapulse.brain.export     │
           │  ── fetch_all()             │
           │  ── render_session(row)     │
           │  ── render_decision(row)    │
           │  ── render_incident(row)    │
           │  ── render_knowledge(row)   │
           │  ── render_layer_index()    │
           │  ── render_module_index()   │
           │  ── write_vault()           │
           └───────────────┬─────────────┘
                           ▼
           ┌─────────────────────────────┐
           │  docs/brain/vault/           │
           │  ├── README.md               │
           │  ├── sessions/*.md           │
           │  ├── decisions/*.md          │
           │  ├── incidents/*.md          │
           │  ├── knowledge/*.md          │
           │  ├── layers/*.md  (indexes)  │
           │  └── modules/*.md (indexes)  │
           └─────────────────────────────┘
                           ▼
                    Obsidian graph view
```

### 4.3 File layout in the generated vault

Each generated markdown file has YAML frontmatter + body with wikilinks. Examples:

**`sessions/2026-04-13-hhmm-claude-happy-turing.md`:**

```markdown
---
id: 42
type: session
timestamp: 2026-04-13T11:34
branch: claude/happy-turing
user: Ahmed Shaaban
layers: [bronze, frontend, test]
modules: [brain, core, frontend, graph, migrations, scenarios]
---

# Session: claude/happy-turing — 2026-04-13 11:34

Touched layers: [[layers/bronze]], [[layers/frontend]], [[layers/test]]
Touched modules: [[modules/brain]], [[modules/core]], [[modules/frontend]], [[modules/graph]], [[modules/migrations]], [[modules/scenarios]]

## Files changed
- src/datapulse/brain/db.py
- src/datapulse/graph/store.py
- ...

## Body
<contents of brain.sessions.body_md, preserved verbatim>

## Linked decisions
- [[decisions/42-chose-psycopg2]]

## Linked incidents
- (none)
```

**`layers/bronze.md` (generated index page):**

```markdown
---
type: layer
name: bronze
---

# Layer: bronze

## Sessions touching this layer
- [[sessions/2026-04-11-2140-fix-brain-merge-conflicts]]
- [[sessions/2026-04-13-1134-claude-happy-turing]]
- ...

## Modules in this layer
- [[modules/loader]]
- [[modules/reader]]
- [[modules/column_map]]
```

**`decisions/42-chose-psycopg2.md`:**

```markdown
---
id: 42
type: decision
session_id: 38
tags: [architecture, database]
---

# Chose psycopg2 over asyncpg

Part of session [[sessions/2026-04-10-hhmm-some-branch]]

<body_md verbatim>

Tags: [[tags/architecture]], [[tags/database]]
```

### 4.4 CLI interface

```bash
# Full rebuild (default) — deletes vault/ and regenerates
python -m datapulse.brain.export --out docs/brain/vault

# Incremental — only rows created/updated since last run
python -m datapulse.brain.export --out docs/brain/vault --mode incremental

# Dry run — print what would be written, touch nothing
python -m datapulse.brain.export --out docs/brain/vault --dry-run

# Limit by type (handy for debugging)
python -m datapulse.brain.export --only sessions,decisions
```

The CLI lives at `src/datapulse/brain/export.py` and exposes `main(argv)` for testability.

### 4.5 Incremental mode bookkeeping

Store the last-sync timestamp in `docs/brain/vault/.last_sync` (gitignored). On incremental runs, `WHERE created_at > last_sync` (or `updated_at` for knowledge). Session deletions are not reflected — rebuild mode handles that.

### 4.6 Makefile / automation

Add to `Makefile`:

```
brain-sync:
	python -m datapulse.brain.export --out docs/brain/vault

brain-sync-incremental:
	python -m datapulse.brain.export --out docs/brain/vault --mode incremental
```

Optional n8n workflow (later, not in this PR): daily cron that pulls + commits vault updates.

### 4.7 Testing

- **Unit tests** (`tests/test_brain_export.py`):
  - `render_session()` produces expected frontmatter + wikilinks given a fixture row.
  - `render_layer_index()` deduplicates sessions and sorts by timestamp.
  - `slugify()` handles branch names with slashes, Arabic, mixed case.
  - Incremental mode filters correctly given `.last_sync`.
- **Integration test** (opt-in, skipped when `DATABASE_URL` unset): rebuild against a live brain DB and assert at least one session file + one layer index file exist.
- No E2E tests — Obsidian rendering is visual; manual verification instead.

### 4.8 Out of scope for Phase 2

- Two-way sync (vault → DB).
- Edges table in PostgreSQL.
- API endpoints exposing the graph.
- A web UI for browsing the vault (Obsidian is the UI).
- Automatic commit / push of the vault.

---

## 5. Error Handling

### Phase 1

Refactoring PR — errors surface as test failures or import errors. Standard process: fix before merging.

### Phase 2

- DB connection failure → exit code 2, log the failed host/port, do not write partial vault.
- Single-row render failure → log the row id and continue (don't let one bad row abort the whole export); exit code 1 if any row failed.
- Output directory exists but not a git-tracked `vault/` → refuse with clear message, require `--force`.
- `OPENROUTER_API_KEY` absent → ignored (embeddings not needed for export).

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Import-path churn breaks downstream code | Medium | High | Re-export everything through `__init__.py` barrels; run full test suite after each file split |
| Silent behavior change during split | Low | High | Splits are pure code moves; test suite is the safety net; `ruff` catches unused imports |
| Droplet DB unreachable from local | Medium | Medium | Reuse existing `brain.db.get_connection()` which already handles this; document SSH tunnel fallback in vault README |
| Vault diff noise in git | Medium | Low | Add `docs/brain/vault/` to `.gitignore` by default (like `sessions/`); only commit manually when snapshotting |
| Obsidian wikilink resolution edge cases (spaces, Arabic) | Low | Low | Slug everything; include a URL-safe slug test in unit tests |

---

## 7. Testing & Acceptance

### Phase 1 acceptance

- [ ] `find src/datapulse -name "*.py" -exec wc -l {} \; | awk '$1 > 800'` returns empty.
- [ ] `grep -rn "^def _set_cache" src/` finds exactly one definition.
- [ ] `ruff format --check src/ tests/` — clean.
- [ ] `ruff check src/ tests/` — clean.
- [ ] `pytest --cov-fail-under=95` — green.
- [ ] `docker compose up` smoke test — API returns 200 on `/api/v1/health`.
- [ ] PR description includes "no behavior change" assertion with test evidence.

### Phase 2 acceptance

- [ ] `python -m datapulse.brain.export --out /tmp/vault --dry-run` prints intended writes.
- [ ] `python -m datapulse.brain.export --out docs/brain/vault` produces:
  - `sessions/*.md` for every row in `brain.sessions`
  - `decisions/*.md` for every row in `brain.decisions`
  - `incidents/*.md` for every row in `brain.incidents`
  - `knowledge/*.md` for every row in `brain.knowledge`
  - `layers/*.md` index per distinct layer across sessions
  - `modules/*.md` index per distinct module across sessions
- [ ] Opening `docs/brain/vault/` in Obsidian and enabling graph view shows session nodes connected to layer/module/decision/incident nodes.
- [ ] `tests/test_brain_export.py` — green with `pytest -m unit`.
- [ ] `make brain-sync` works end-to-end.

---

## 8. Dependencies Between Phases

Phase 2 does **not** depend on Phase 1. But shipping them sequentially:
- Keeps PRs small and reviewable.
- Phase 1 refactors may rename modules → cleaner module names in Phase 2's `modules/*.md` pages.
- Reduces merge-conflict surface.

---

## 9. Open Questions

None remaining. All three clarifying questions answered:
1. Brain relations → markdown-only export (no schema change).
2. Execution order → sequential (Phase 1 first).
3. Review depth → structural only (split big files, consolidate duplicates, no behavior change).

---

## 10. Next Step

Invoke the `writing-plans` skill to produce the step-by-step implementation plan for Phase 1 (the plan for Phase 2 will be written after Phase 1 merges).
