# Phase 1 Simplification Sprint — Handoff at Task 4/9

**Date:** 2026-04-16
**Branch:** `claude/zen-einstein` (pushed to origin)
**Handed off by:** Ahmed Shaaban session

---

## What's DONE (Tasks 0–4, all committed + pushed)

| Commit | Task | What |
|--------|------|------|
| `b706e475` | Task 0 | Baseline: lint clean, 2007 unit tests pass, coverage 76.53% |
| `d36185ac` | Task 1 | Split `control_center/repository.py` 937 → 7 per-class files |
| `f04e7510` | Task 2 | Split `analytics/models.py` 675 → 7 per-domain files (47 Pydantic classes) |
| `f32db2fc` | Task 3 | Split `api/routes/control_center.py` 912 → 5 sub-routers + `_deps.py` |
| `ce8fcd08` | Task 4 | Split `api/routes/analytics.py` 657 → 6 sub-routers + `_shared.py` |

## What's REMAINING (Tasks 5–9)

| Task | File | LOC | Approach |
|------|------|-----|----------|
| **Task 5** | `control_center/service.py` | 865 | Split 33 methods into 4 domain services (sources/pipelines/mappings/sync) + thin facade |
| **Task 6** | `analytics/service.py` | 651 | Same facade pattern, 6 domains (kpi/ranking/breakdown/detail/churn/health) |
| **Task 7** | `analytics/kpi_repository.py` | 778 | Extract SQL templates to `kpi_queries.py`, keep class as orchestrator |
| **Task 8** | `scheduler.py` | 646 | Split into `scheduler/` package: executor.py + triggers.py + models.py |
| **Task 9** | Final quality sweep | — | Ruff + pytest + graph reindex + open PR |

## Key Files

- **Design spec:** `docs/superpowers/specs/2026-04-15-cleanup-and-brain-obsidian-design.md`
- **Implementation plan:** `docs/superpowers/plans/2026-04-15-phase-1-simplification-sprint.md`
- Full step-by-step for every remaining task is in the plan doc.

## Invariants to Maintain

1. **Import paths preserved** — barrel `__init__.py` re-exports every public symbol
2. **Local test gate:** `pytest -m unit` green, coverage >= 76.93%
3. **Lint gate:** `ruff format --check src/ tests/` + `ruff check src/ tests/` = clean
4. **No behavior changes** — only file moves + barrel re-exports
5. **No local Docker** — full 95% coverage gate runs on droplet at Task 9 before merge

## Pattern Established (Tasks 1–4)

Every split follows this recipe:
1. Read original file, confirm class/method boundaries via `grep -n "^class\|^def"` 
2. Create new package directory with one file per concept
3. Write barrel `__init__.py` that re-exports everything
4. Delete original monolith (Python package replaces it)
5. `ruff check --fix` + `ruff format` the new package
6. Smoke-test: `PYTHONPATH=src python -c "from datapulse.X import Y; print('ok')"`
7. Run `pytest -x -q -m unit --cov=src/datapulse`
8. Commit: `refactor(<module>): split NNN-LOC file.py into M files`

## Phase 2 (Brain → Obsidian Export)

Spec written (same spec file §4) but implementation plan is deferred until Phase 1 merges. Do NOT start Phase 2 until Tasks 5–9 are done and the PR is merged.
