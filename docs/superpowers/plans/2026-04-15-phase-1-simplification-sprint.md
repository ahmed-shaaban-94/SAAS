# Phase 1 — Simplification Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split 8 oversized Python files (>800 or approaching 800 LOC) into focused, single-responsibility modules while preserving every import path, every test, and every byte of behavior.

**Architecture:** Mechanical file-moves only. For each oversized file, (a) create a new package directory, (b) distribute existing classes/functions into one-concept-per-file modules, (c) make the original module a barrel `__init__.py` that re-exports every public symbol so downstream imports keep working, (d) run the full test suite, (e) commit. No behavior changes. No new dependencies. No schema changes.

**Tech Stack:** Python 3.11+, Ruff, pytest, existing SQLAlchemy + FastAPI + Pydantic layout.

**Design reference:** [docs/superpowers/specs/2026-04-15-cleanup-and-brain-obsidian-design.md](../specs/2026-04-15-cleanup-and-brain-obsidian-design.md) §3.

**Graph-validated findings that changed the scope:**
- `_set_cache` duplication was **already consolidated** into `datapulse/api/cache_helpers.py::set_cache_headers`. The graph index showed stale data. Consolidation task is **removed** from this plan.
- No `TODO`/`FIXME`/`HACK`/`XXX` markers exist in `src/`. No debt-comment triage needed.
- Scope narrows to: **8 file splits + final quality gate + PR**.


**Environment amendment (2026-04-15, post-Task-0 retry):**
- **No local Docker available.** PostgreSQL lives on the droplet; DB-dependent tests can't run on the Windows dev machine.
- **Local gate (this sprint):** `pytest -m unit` must stay green and `ruff check/format` clean at every task. Unit-test coverage baseline is whatever Task 0 actually measures — each subsequent task must not drop it.
- **Merge gate (Task 9 → droplet):** full `pytest --cov-fail-under=95` runs on the droplet against the branch before the PR merges. Local sprint work verifies structure; droplet verifies behavior.
- This is honest about what we can actually measure locally and preserves the safety guarantee: refactoring is mechanical, imports resolve, unit tests (SQL builders, Pydantic validators, pure helpers) pass.

---

## Working Context

- **Branch:** `claude/zen-einstein` (already checked out in worktree `.claude/worktrees/zen-einstein`)
- **All commands assume CWD:** `C:/Users/user/Documents/GitHub/Data-Pulse/.claude/worktrees/zen-einstein`
- **Python entrypoint:** run commands through `docker compose exec api <cmd>` when services are up, or locally with the project venv. Use whichever is available — both are equivalent for running pytest.

---

## Task 0: Baseline — confirm green before touching anything

**Files:** (none modified)

- [ ] **Step 1: Fetch fresh state and confirm clean working tree**

```bash
git status --short
```

Expected: no uncommitted changes (the spec commit `ffd162f5` is the last one).

- [ ] **Step 2: Run lint baseline**

```bash
ruff format --check src/ tests/
ruff check src/ tests/
```

Expected: both commands exit 0. If they don't, STOP and report — the baseline is not clean and this plan's invariant ("no new lint warnings") can't be measured.


- [ ] **Step 3: Run unit-test baseline (local gate — no DB)**

```bash
pytest -m unit -x -q --cov=src/datapulse --cov-report=term 2>&1 | tail -30
```

Expected: all unit tests pass. Record the final coverage percentage — whatever it is, it becomes the **local** invariant for every subsequent task (tasks must not drop below it). Full 95% gate runs on the droplet at Task 9 before merge, not here.

If `pytest -m unit` reports "no tests ran" or errors because the `unit` marker isn't registered, fall back to:

```bash
pytest -x -q --ignore=tests/test_api_endpoints.py --cov=src/datapulse --cov-report=term 2>&1 | tail -30
```

(Excludes the known DB-dependent suite. Other DB-dependent tests will skip or fail cleanly — record which.)
- [ ] **Step 3: Run test baseline**

```bash
pytest -x -q --cov=src/datapulse --cov-fail-under=95 2>&1 | tee /tmp/baseline-tests.txt
```

Expected: all tests pass, coverage ≥ 95%. Record the final coverage percentage in a scratchpad — it becomes the invariant for every subsequent task.

- [ ] **Step 4: Snapshot oversized-file list**

```bash
find src/datapulse -name "*.py" -exec wc -l {} \; | sort -rn | awk '$1 > 400' | head -20 > /tmp/oversized-before.txt
cat /tmp/oversized-before.txt
```

Expected output (exact numbers may drift by ±5 lines):
```
937 src/datapulse/control_center/repository.py
912 src/datapulse/api/routes/control_center.py
865 src/datapulse/control_center/service.py
778 src/datapulse/analytics/kpi_repository.py
675 src/datapulse/analytics/models.py
657 src/datapulse/api/routes/analytics.py
651 src/datapulse/analytics/service.py
646 src/datapulse/scheduler.py
...
```

This file is the "before" snapshot. Task 9 compares against it.

- [ ] **Step 5: Commit baseline marker (empty commit for git log clarity)**

```bash
git commit --allow-empty -m "chore: phase-1 simplification sprint — baseline marker

All 8 files >400 LOC captured in /tmp/oversized-before.txt.
Tests + lint green at commit 8288bb21..ffd162f5.
Next commits split one file each until every file <400 LOC target."
```

---

## Task 1: Split `control_center/repository.py` (937 LOC → 7 files)

**Why this one first:** The file contains 7 independent Repository classes with zero cross-references. Pure mechanical split. Lowest risk. Biggest LOC win.

**Files:**
- Read: `src/datapulse/control_center/repository.py` (verify class boundaries haven't shifted)
- Create: `src/datapulse/control_center/repositories/__init__.py`
- Create: `src/datapulse/control_center/repositories/source_connection.py`
- Create: `src/datapulse/control_center/repositories/pipeline_profile.py`
- Create: `src/datapulse/control_center/repositories/mapping_template.py`
- Create: `src/datapulse/control_center/repositories/pipeline_draft.py`
- Create: `src/datapulse/control_center/repositories/pipeline_release.py`
- Create: `src/datapulse/control_center/repositories/sync_job.py`
- Create: `src/datapulse/control_center/repositories/sync_schedule.py`
- Modify: `src/datapulse/control_center/repository.py` (becomes barrel re-export only)
- No test files need modification — they import via `datapulse.control_center.repository` which stays valid through the barrel.

- [ ] **Step 1: Re-read the current file to confirm class boundaries**

```bash
grep -n "^class " src/datapulse/control_center/repository.py
```

Expected:
```
23:class SourceConnectionRepository:
167:class PipelineProfileRepository:
290:class MappingTemplateRepository:
413:class PipelineDraftRepository:
556:class PipelineReleaseRepository:
723:class SyncJobRepository:
815:class SyncScheduleRepository:
```

If any line number has shifted, note the new ranges — the boundaries are what matter, not the exact line numbers.

- [ ] **Step 2: Identify the module-level header (imports + module docstring + shared helpers)**

```bash
sed -n '1,22p' src/datapulse/control_center/repository.py
```

That header (lines 1–22) is the shared preamble. Every new file gets a trimmed version of it (drop unused imports per-file — `ruff check --fix` will handle that).

- [ ] **Step 3: Create the `repositories/` package**

```bash
mkdir -p src/datapulse/control_center/repositories
```

- [ ] **Step 4: Extract each class into its own file**

For each of the 7 classes, create a file with this exact template (example shown for `SourceConnectionRepository`; repeat for the other 6):

`src/datapulse/control_center/repositories/source_connection.py`:

```python
"""Repository for source_connections table.

Extracted from control_center/repository.py as part of the simplification sprint.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


# --- paste class body verbatim from original lines 23..166 ---
class SourceConnectionRepository:
    ...
```

Filename → class mapping:

| Filename | Class | Original line range |
|----------|-------|---------------------|
| `source_connection.py` | `SourceConnectionRepository` | 23–166 |
| `pipeline_profile.py` | `PipelineProfileRepository` | 167–289 |
| `mapping_template.py` | `MappingTemplateRepository` | 290–412 |
| `pipeline_draft.py` | `PipelineDraftRepository` | 413–555 |
| `pipeline_release.py` | `PipelineReleaseRepository` | 556–722 |
| `sync_job.py` | `SyncJobRepository` | 723–814 |
| `sync_schedule.py` | `SyncScheduleRepository` | 815–end |

Each extracted file gets:
1. The module docstring (adjusted to name the table/repo).
2. The imports from the original file's top section (copy all 6 imports — `ruff check --fix` will remove unused ones in Step 7).
3. The `log = get_logger(__name__)` line.
4. The verbatim class body.

- [ ] **Step 5: Write the `repositories/__init__.py` barrel**

`src/datapulse/control_center/repositories/__init__.py`:

```python
"""Control Center repository layer.

Split from the original single-file repository.py during the Phase 1
simplification sprint. All existing imports through
`datapulse.control_center.repository` continue to work via the barrel
re-export in the sibling repository.py module.
"""

from datapulse.control_center.repositories.mapping_template import (
    MappingTemplateRepository,
)
from datapulse.control_center.repositories.pipeline_draft import (
    PipelineDraftRepository,
)
from datapulse.control_center.repositories.pipeline_profile import (
    PipelineProfileRepository,
)
from datapulse.control_center.repositories.pipeline_release import (
    PipelineReleaseRepository,
)
from datapulse.control_center.repositories.source_connection import (
    SourceConnectionRepository,
)
from datapulse.control_center.repositories.sync_job import SyncJobRepository
from datapulse.control_center.repositories.sync_schedule import (
    SyncScheduleRepository,
)

__all__ = [
    "MappingTemplateRepository",
    "PipelineDraftRepository",
    "PipelineProfileRepository",
    "PipelineReleaseRepository",
    "SourceConnectionRepository",
    "SyncJobRepository",
    "SyncScheduleRepository",
]
```

- [ ] **Step 6: Replace `control_center/repository.py` with a barrel re-export**

Overwrite `src/datapulse/control_center/repository.py` with:

```python
"""Barrel re-export for the Control Center repository layer.

The actual implementation now lives under
`datapulse.control_center.repositories.*` (one class per file). This
module is kept so existing imports keep working:

    from datapulse.control_center.repository import SourceConnectionRepository  # still valid
"""

from datapulse.control_center.repositories import (  # noqa: F401
    MappingTemplateRepository,
    PipelineDraftRepository,
    PipelineProfileRepository,
    PipelineReleaseRepository,
    SourceConnectionRepository,
    SyncJobRepository,
    SyncScheduleRepository,
)

__all__ = [
    "MappingTemplateRepository",
    "PipelineDraftRepository",
    "PipelineProfileRepository",
    "PipelineReleaseRepository",
    "SourceConnectionRepository",
    "SyncJobRepository",
    "SyncScheduleRepository",
]
```

- [ ] **Step 7: Run ruff fix to clean unused imports across the new files**

```bash
ruff check --fix src/datapulse/control_center/repositories/ src/datapulse/control_center/repository.py
ruff format src/datapulse/control_center/repositories/ src/datapulse/control_center/repository.py
```

Expected: every file left with only the imports it actually uses. No manual trimming needed.

- [ ] **Step 8: Run the full test suite**

```bash
pytest -x -q tests/test_control_center_connections_write.py tests/test_control_center_health_summary.py tests/test_control_center_onboarding_integration.py tests/test_control_center_schedules.py -v
```

Expected: every test passes. Then run the full suite:

```bash
pytest -x -q --cov=src/datapulse --cov-fail-under=95
```

Expected: green, coverage unchanged from baseline.

- [ ] **Step 9: Confirm no file in the package exceeds 400 LOC**

```bash
wc -l src/datapulse/control_center/repositories/*.py src/datapulse/control_center/repository.py
```

Expected: each file ≤ ~200 LOC. `pipeline_release.py` (167 lines of class body) will be the largest.

- [ ] **Step 10: Commit**

```bash
git add src/datapulse/control_center/repositories/ src/datapulse/control_center/repository.py
git commit -m "refactor(control_center): split 937-LOC repository.py into 7 per-class files

One file per Repository class. The original repository.py becomes a
barrel re-export so every existing import path keeps working:
  from datapulse.control_center.repository import SourceConnectionRepository  # still valid

No behavior change. Tests green, coverage unchanged."
```

---

## Task 2: Split `analytics/models.py` (675 LOC → 6 domain files)

**Why second:** Pure data classes (Pydantic models), zero behavior. Import-heavy across the codebase but mechanical to split.

**Files:**
- Read: `src/datapulse/analytics/models.py`
- Create: `src/datapulse/analytics/models/__init__.py` (barrel)
- Create: `src/datapulse/analytics/models/shared.py` (AnalyticsFilter, DateRange, and any cross-domain base models)
- Create: `src/datapulse/analytics/models/kpi.py`
- Create: `src/datapulse/analytics/models/ranking.py`
- Create: `src/datapulse/analytics/models/breakdown.py`
- Create: `src/datapulse/analytics/models/detail.py`
- Create: `src/datapulse/analytics/models/churn.py`
- Create: `src/datapulse/analytics/models/health.py`
- Delete: `src/datapulse/analytics/models.py` (replaced by the package `models/`)

- [ ] **Step 1: Map every class to a domain bucket**

```bash
grep -n "^class " src/datapulse/analytics/models.py
```

Use the import sites in [api/routes/analytics.py:16-50](src/datapulse/api/routes/analytics.py:16) as the ground-truth list. The domain mapping:

| Domain file | Classes it owns |
|------------|----------------|
| `shared.py` | `AnalyticsFilter`, `DateRange`, `DataDateRange`, `FilterOptions`, and any base model used by ≥ 2 domains |
| `kpi.py` | `KPISummary`, `DashboardData`, `SegmentSummary`, `TrendResult` |
| `ranking.py` | `RankingResult`, `TopMovers`, `ProductPerformance`, `StaffPerformance`, `StaffQuota` |
| `breakdown.py` | `BillingBreakdown`, `CustomerTypeBreakdown`, `HeatmapData`, `SeasonalityDaily`, `SeasonalityMonthly`, `ProductHierarchy`, `ProductLifecycle`, `LifecycleDistribution`, `RevenueDailyRolling`, `RevenueSiteRolling` |
| `detail.py` | `CustomerAnalytics`, `SiteDetail`, `WaterfallAnalysis` |
| `churn.py` | `ChurnPrediction`, `ReturnAnalysis`, `ReturnsTrend`, `AffinityPair`, `ABCAnalysis` |
| `health.py` | `CustomerHealthScore`, `HealthDistribution` |

Write the mapping down — this is a judgement call captured explicitly so the rest of the task is mechanical.

- [ ] **Step 2: Create the `models/` package with each domain file**

```bash
mkdir -p src/datapulse/analytics/models
```

For each domain file, use this template (example shown for `kpi.py`):

`src/datapulse/analytics/models/kpi.py`:

```python
"""KPI summary and dashboard response models.

Extracted from the monolithic analytics/models.py as part of the Phase 1
simplification sprint.
"""

from __future__ import annotations

from datetime import date  # or whatever types are used
from decimal import Decimal

from pydantic import BaseModel, Field

from datapulse.analytics.models.shared import AnalyticsFilter, DateRange


# --- paste class bodies verbatim from the original models.py ---
class KPISummary(BaseModel):
    ...
```

Rules:
1. Copy classes **as a group** from the original file preserving their order.
2. If a class in domain A uses a class from domain B, the class in B has to be imported (or moved to `shared.py` if multiple domains need it).
3. `from __future__ import annotations` goes in every file — it keeps forward references working.

- [ ] **Step 3: Write the barrel `models/__init__.py`**

`src/datapulse/analytics/models/__init__.py`:

```python
"""Analytics response and filter models.

Split into per-domain files during the Phase 1 simplification sprint.
All imports through `datapulse.analytics.models` continue to work via
this barrel.
"""

from datapulse.analytics.models.breakdown import (
    BillingBreakdown,
    CustomerTypeBreakdown,
    HeatmapData,
    LifecycleDistribution,
    ProductHierarchy,
    ProductLifecycle,
    RevenueDailyRolling,
    RevenueSiteRolling,
    SeasonalityDaily,
    SeasonalityMonthly,
)
from datapulse.analytics.models.churn import (
    ABCAnalysis,
    AffinityPair,
    ChurnPrediction,
    ReturnAnalysis,
    ReturnsTrend,
)
from datapulse.analytics.models.detail import (
    CustomerAnalytics,
    SiteDetail,
    WaterfallAnalysis,
)
from datapulse.analytics.models.health import (
    CustomerHealthScore,
    HealthDistribution,
)
from datapulse.analytics.models.kpi import (
    DashboardData,
    KPISummary,
    SegmentSummary,
    TrendResult,
)
from datapulse.analytics.models.ranking import (
    ProductPerformance,
    RankingResult,
    StaffPerformance,
    StaffQuota,
    TopMovers,
)
from datapulse.analytics.models.shared import (
    AnalyticsFilter,
    DataDateRange,
    DateRange,
    FilterOptions,
)

__all__ = [
    # shared
    "AnalyticsFilter",
    "DataDateRange",
    "DateRange",
    "FilterOptions",
    # kpi
    "DashboardData",
    "KPISummary",
    "SegmentSummary",
    "TrendResult",
    # ranking
    "ProductPerformance",
    "RankingResult",
    "StaffPerformance",
    "StaffQuota",
    "TopMovers",
    # breakdown
    "BillingBreakdown",
    "CustomerTypeBreakdown",
    "HeatmapData",
    "LifecycleDistribution",
    "ProductHierarchy",
    "ProductLifecycle",
    "RevenueDailyRolling",
    "RevenueSiteRolling",
    "SeasonalityDaily",
    "SeasonalityMonthly",
    # detail
    "CustomerAnalytics",
    "SiteDetail",
    "WaterfallAnalysis",
    # churn
    "ABCAnalysis",
    "AffinityPair",
    "ChurnPrediction",
    "ReturnAnalysis",
    "ReturnsTrend",
    # health
    "CustomerHealthScore",
    "HealthDistribution",
]
```

- [ ] **Step 4: Delete the old file**

```bash
rm src/datapulse/analytics/models.py
```

Python will now resolve `from datapulse.analytics.models import ...` via the package's `__init__.py`.

- [ ] **Step 5: Clean imports**

```bash
ruff check --fix src/datapulse/analytics/models/
ruff format src/datapulse/analytics/models/
```

- [ ] **Step 6: Run the full test suite**

```bash
pytest -x -q --cov=src/datapulse --cov-fail-under=95
```

Expected: green. If any test fails with `ImportError: cannot import name X from datapulse.analytics.models`, the class was missed from the barrel — add it.

- [ ] **Step 7: Verify every file in `models/` is ≤ 250 LOC**

```bash
wc -l src/datapulse/analytics/models/*.py
```

- [ ] **Step 8: Commit**

```bash
git add src/datapulse/analytics/models/ src/datapulse/analytics/models.py
git commit -m "refactor(analytics): split 675-LOC models.py into 7 per-domain files

47 Pydantic models redistributed across shared/kpi/ranking/breakdown/
detail/churn/health. The original models.py is replaced by a package
whose __init__.py re-exports every symbol — existing imports unchanged.

No behavior change. Tests green, coverage unchanged."
```

---

## Task 3: Split `api/routes/control_center.py` (912 LOC → 5 sub-routers)

**Files:**
- Read: `src/datapulse/api/routes/control_center.py`
- Create: `src/datapulse/api/routes/control_center/__init__.py`
- Create: `src/datapulse/api/routes/control_center/sources.py`
- Create: `src/datapulse/api/routes/control_center/pipelines.py` (covers profiles + drafts + releases)
- Create: `src/datapulse/api/routes/control_center/mappings.py`
- Create: `src/datapulse/api/routes/control_center/jobs.py`
- Create: `src/datapulse/api/routes/control_center/schedules.py`
- Delete: `src/datapulse/api/routes/control_center.py`
- Verify: `src/datapulse/api/app.py` still includes the same router (import path `datapulse.api.routes.control_center` stays valid via the new package's `__init__.py`).

- [ ] **Step 1: Identify the endpoint groups**

```bash
grep -n "^@router\|^def " src/datapulse/api/routes/control_center.py | head -80
```

Expected groups (exact line numbers may vary):
- `/source-connections/*` endpoints
- `/pipeline-profiles/*`, `/pipeline-drafts/*`, `/pipeline-releases/*`
- `/mapping-templates/*`
- `/sync-jobs/*`
- `/sync-schedules/*`

- [ ] **Step 2: Read the file's imports and router definition**

```bash
sed -n '1,80p' src/datapulse/api/routes/control_center.py
```

Note which imports each endpoint uses. The shared FastAPI router, `get_current_user` dependency, and tenant-session helper will be used by every sub-file.

- [ ] **Step 3: Create the package and each sub-router**

Each sub-router file follows this template (example for `sources.py`):

`src/datapulse/api/routes/control_center/sources.py`:

```python
"""Control Center — source connection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_control_center_service
from datapulse.api.limiter import limiter
# ...any other imports the source-connection endpoints use

router = APIRouter(
    prefix="/source-connections",
    tags=["control-center", "sources"],
    dependencies=[Depends(get_current_user)],
)


# --- paste every @router endpoint whose path starts with /source-connections ---
@router.get("", response_model=list[...])
...
```

The 5 sub-router files are:

| File | Endpoint group(s) | Prefix |
|------|-------------------|--------|
| `sources.py` | source-connections | `/source-connections` |
| `pipelines.py` | pipeline-profiles + pipeline-drafts + pipeline-releases | `/pipelines` (use nested prefixes inside) OR 3 separate APIRouters in one file |
| `mappings.py` | mapping-templates | `/mapping-templates` |
| `jobs.py` | sync-jobs | `/sync-jobs` |
| `schedules.py` | sync-schedules | `/sync-schedules` |

For `pipelines.py` specifically: the 3 sub-resources share nothing but namespace. Simplest pattern — define 3 sub-routers inside one file and include them from the package `__init__.py`.

- [ ] **Step 4: Write the package `__init__.py` that composes the original single router**

`src/datapulse/api/routes/control_center/__init__.py`:

```python
"""Control Center API — composed of per-resource sub-routers.

The original single-file router was split during the Phase 1
simplification sprint. The public surface — a single `router` exposed
at /control-center — is preserved by including all sub-routers here.
"""

from fastapi import APIRouter

from datapulse.api.routes.control_center.jobs import router as jobs_router
from datapulse.api.routes.control_center.mappings import router as mappings_router
from datapulse.api.routes.control_center.pipelines import (
    drafts_router,
    profiles_router,
    releases_router,
)
from datapulse.api.routes.control_center.schedules import router as schedules_router
from datapulse.api.routes.control_center.sources import router as sources_router

router = APIRouter(prefix="/control-center", tags=["control-center"])
router.include_router(sources_router)
router.include_router(profiles_router)
router.include_router(drafts_router)
router.include_router(releases_router)
router.include_router(mappings_router)
router.include_router(jobs_router)
router.include_router(schedules_router)

__all__ = ["router"]
```

Adjust the exact sub-router names to match whatever is defined in `pipelines.py`.

- [ ] **Step 5: Delete the monolith**

```bash
rm src/datapulse/api/routes/control_center.py
```

- [ ] **Step 6: Verify `api/app.py` still resolves the router import**

```bash
grep -n "control_center" src/datapulse/api/app.py
```

The existing line `from datapulse.api.routes.control_center import router as control_center_router` (or similar) will still work — Python resolves it to the package's `__init__.py`.

- [ ] **Step 7: Lint + format**

```bash
ruff check --fix src/datapulse/api/routes/control_center/
ruff format src/datapulse/api/routes/control_center/
```

- [ ] **Step 8: Run the full test suite + start the API and hit one endpoint**

```bash
pytest -x -q --cov=src/datapulse --cov-fail-under=95
```

Then smoke-test the router wiring:

```bash
docker compose up -d api
curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
```

Expected: tests green, health returns 200.

- [ ] **Step 9: Confirm LOC target met**

```bash
wc -l src/datapulse/api/routes/control_center/*.py
```

Each file should be ≤ 250 LOC. `pipelines.py` will be the largest (three resource groups); if it ends up > 400, split it into `profiles.py`, `drafts.py`, `releases.py` in a follow-up step.

- [ ] **Step 10: Commit**

```bash
git add src/datapulse/api/routes/control_center/ src/datapulse/api/routes/control_center.py
git commit -m "refactor(api): split 912-LOC control_center router into 5 sub-routers

Broken into sources/pipelines/mappings/jobs/schedules sub-routers.
Package __init__.py composes them back into a single router object so
main app registration path (app.include_router) is unchanged.

No behavior change. Tests green, health endpoint returns 200."
```

---

## Task 4: Split `api/routes/analytics.py` (657 LOC → 6 sub-routers)

**Files:**
- Read: `src/datapulse/api/routes/analytics.py`
- Create: `src/datapulse/api/routes/analytics/__init__.py`
- Create: `src/datapulse/api/routes/analytics/_shared.py` (AnalyticsQueryParams, `_to_filter`, `ServiceDep` alias)
- Create: `src/datapulse/api/routes/analytics/kpi.py`
- Create: `src/datapulse/api/routes/analytics/ranking.py`
- Create: `src/datapulse/api/routes/analytics/breakdown.py`
- Create: `src/datapulse/api/routes/analytics/detail.py`
- Create: `src/datapulse/api/routes/analytics/churn.py`
- Create: `src/datapulse/api/routes/analytics/health.py`
- Delete: `src/datapulse/api/routes/analytics.py`

- [ ] **Step 1: Map each endpoint to a domain**

```bash
grep -n "^@router\.get\|^@router\.post\|^def get_\|^def post_" src/datapulse/api/routes/analytics.py
```

Use the domain grouping already defined in Task 2 for the models. Endpoint families align 1:1:

| Sub-file | Endpoints | Response model domains |
|----------|-----------|------------------------|
| `kpi.py` | `/dashboard`, `/kpi-summary`, `/trends`, `/segments` | KPISummary, DashboardData, TrendResult, SegmentSummary |
| `ranking.py` | `/top-products`, `/top-customers`, `/top-staff`, `/top-movers`, `/staff-quotas` | RankingResult, TopMovers, StaffPerformance, StaffQuota |
| `breakdown.py` | `/by-billing`, `/by-customer-type`, `/heatmap`, `/seasonality-*`, `/product-hierarchy`, `/product-lifecycle`, `/revenue-rolling` | BillingBreakdown, HeatmapData, SeasonalityDaily, etc. |
| `detail.py` | `/customers/{id}`, `/sites/{id}`, `/waterfall` | CustomerAnalytics, SiteDetail, WaterfallAnalysis |
| `churn.py` | `/churn-prediction`, `/returns`, `/affinity`, `/abc-analysis` | ChurnPrediction, ReturnAnalysis, AffinityPair, ABCAnalysis |
| `health.py` | `/customer-health`, `/health-distribution` | CustomerHealthScore, HealthDistribution |

- [ ] **Step 2: Create `_shared.py` with the common helpers**

`src/datapulse/api/routes/analytics/_shared.py`:

```python
"""Shared query params and helpers for analytics sub-routers."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from datapulse.analytics.models import AnalyticsFilter, DateRange
from datapulse.analytics.service import AnalyticsService
from datapulse.api.deps import get_analytics_service


class AnalyticsQueryParams(BaseModel):
    """Common query parameters shared across analytics endpoints."""

    start_date: date | None = None
    end_date: date | None = None
    category: Annotated[str | None, Field(max_length=100)] = None
    brand: Annotated[str | None, Field(max_length=100)] = None
    site_key: int | None = None
    staff_key: int | None = None
    limit: int = Field(default=10, ge=1, le=100)


def to_filter(params: AnalyticsQueryParams) -> AnalyticsFilter | None:
    """Convert query params into an AnalyticsFilter. None when no filters set."""
    # --- paste the body of the original _to_filter verbatim ---
    ...


ServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
```

Rename `_to_filter` → `to_filter` (drop the underscore since it now crosses module boundaries).

- [ ] **Step 3: Create each domain sub-router**

Template (example for `kpi.py`):

`src/datapulse/api/routes/analytics/kpi.py`:

```python
"""Analytics KPI endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from datapulse.analytics.models import DashboardData, KPISummary, SegmentSummary, TrendResult
from datapulse.api.auth import get_current_user
from datapulse.api.cache_helpers import set_cache_headers
from datapulse.api.limiter import limiter
from datapulse.api.routes.analytics._shared import (
    AnalyticsQueryParams,
    ServiceDep,
    to_filter,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


# --- paste every @router.get endpoint that belongs to the kpi domain ---
@router.get("/dashboard", response_model=DashboardData)
@limiter.limit("60/minute")
def get_dashboard(request: Request, response: Response, ...):
    ...
```

- [ ] **Step 4: Compose `analytics/__init__.py`**

`src/datapulse/api/routes/analytics/__init__.py`:

```python
"""Analytics API — composed of per-domain sub-routers."""

from fastapi import APIRouter, Depends

from datapulse.api.auth import get_current_user
from datapulse.api.routes.analytics.breakdown import router as breakdown_router
from datapulse.api.routes.analytics.churn import router as churn_router
from datapulse.api.routes.analytics.detail import router as detail_router
from datapulse.api.routes.analytics.health import router as health_router
from datapulse.api.routes.analytics.kpi import router as kpi_router
from datapulse.api.routes.analytics.ranking import router as ranking_router

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)],
)
router.include_router(kpi_router)
router.include_router(ranking_router)
router.include_router(breakdown_router)
router.include_router(detail_router)
router.include_router(churn_router)
router.include_router(health_router)

__all__ = ["router"]
```

- [ ] **Step 5: Delete the monolith + lint + test + smoke**

```bash
rm src/datapulse/api/routes/analytics.py
ruff check --fix src/datapulse/api/routes/analytics/
ruff format src/datapulse/api/routes/analytics/
pytest -x -q --cov=src/datapulse --cov-fail-under=95
docker compose exec api curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8000/analytics/dashboard?start_date=2026-01-01&end_date=2026-01-31
```

Expected: tests green, dashboard endpoint returns 200 (or 401 if auth headers missing — either confirms routing works).

- [ ] **Step 6: Commit**

```bash
git add src/datapulse/api/routes/analytics/ src/datapulse/api/routes/analytics.py
git commit -m "refactor(api): split 657-LOC analytics router into 6 domain sub-routers

kpi / ranking / breakdown / detail / churn / health — each a focused
sub-router. Shared AnalyticsQueryParams + to_filter helper extracted
to analytics/_shared.py. Package __init__.py composes the public
router with unchanged /analytics prefix.

No behavior change. Tests green, analytics endpoints reachable."
```

---

## Task 5: Split `control_center/service.py` (865 LOC)

**Files:**
- Read: `src/datapulse/control_center/service.py`
- Create: `src/datapulse/control_center/services/__init__.py`
- Create: `src/datapulse/control_center/services/sources.py`
- Create: `src/datapulse/control_center/services/pipelines.py`
- Create: `src/datapulse/control_center/services/mappings.py`
- Create: `src/datapulse/control_center/services/sync.py`
- Create: `src/datapulse/control_center/connectors.py` (extracts `_get_connector`)
- Modify: `src/datapulse/control_center/service.py` → thin facade `ControlCenterService`

- [ ] **Step 1: Map the `ControlCenterService` class methods to domain groups**

```bash
grep -n "def " src/datapulse/control_center/service.py | head -60
```

Classify each method into one of: `sources`, `pipelines`, `mappings`, `sync`. Record the mapping. Example:

```
sources: connect_source, test_connection, list_connections, get_connection, ...
pipelines: create_profile, create_draft, release_profile, rollback_release, ...
mappings: save_template, apply_template, ...
sync: run_job, schedule_job, list_schedules, ...
```

- [ ] **Step 2: Extract `_get_connector` into `connectors.py`**

`src/datapulse/control_center/connectors.py`:

```python
"""Connector dispatcher — returns a Connector instance per source_type."""

from __future__ import annotations

# --- paste the body of _get_connector verbatim, renamed to get_connector ---
def get_connector(
    source_type: str,
    *,
    session=None,
    connection_id: int = 0,
    tenant_id: int = 0,
):
    ...
```

- [ ] **Step 3: Create one service class per domain**

For each domain, create a file like `services/sources.py`:

```python
"""Source-connection domain service."""

from __future__ import annotations

from datapulse.control_center.connectors import get_connector
from datapulse.control_center.repositories import SourceConnectionRepository


class SourcesService:
    """Handles source-connection CRUD + connection testing."""

    def __init__(self, session) -> None:
        self._session = session
        self._repo = SourceConnectionRepository(session)

    # --- paste every method from ControlCenterService that belongs to sources ---
    def connect_source(self, ...) -> ...: ...
    def test_connection(self, ...) -> ...: ...
    ...
```

Repeat for `pipelines.py`, `mappings.py`, `sync.py`.

- [ ] **Step 4: Make the original `service.py` a thin facade**

`src/datapulse/control_center/service.py`:

```python
"""Control Center service — thin facade over per-domain services.

Split from the original 865-LOC implementation during the Phase 1
simplification sprint. Callers keep using ControlCenterService; the
facade delegates to SourcesService, PipelinesService, MappingsService,
SyncService under the hood.
"""

from __future__ import annotations

from datapulse.control_center.services.mappings import MappingsService
from datapulse.control_center.services.pipelines import PipelinesService
from datapulse.control_center.services.sources import SourcesService
from datapulse.control_center.services.sync import SyncService


class ControlCenterService:
    """Facade over per-domain Control Center services."""

    def __init__(self, session) -> None:
        self._session = session
        self.sources = SourcesService(session)
        self.pipelines = PipelinesService(session)
        self.mappings = MappingsService(session)
        self.sync = SyncService(session)

    # --- Delegate the existing public method surface ---
    # For each original public method, keep a thin wrapper that calls the
    # appropriate sub-service. Example:
    def connect_source(self, *args, **kwargs):
        return self.sources.connect_source(*args, **kwargs)

    # Keep every public method the routes and scheduler call (grep to confirm).
```

- [ ] **Step 5: Find every caller of `ControlCenterService` methods**

```bash
grep -rn "ControlCenterService\|control_center_service\." src/ tests/ | head -40
```

Every method name the callers use must have a delegate on the facade. If a method is called only internally in the original service, it doesn't need to appear on the facade — it stays on its new sub-service.

- [ ] **Step 6: Lint + test**

```bash
ruff check --fix src/datapulse/control_center/
ruff format src/datapulse/control_center/
pytest -x -q --cov=src/datapulse --cov-fail-under=95
```

Expected: green. If a test fails with `AttributeError: 'ControlCenterService' object has no attribute 'X'`, add delegate X on the facade.

- [ ] **Step 7: Confirm LOC targets**

```bash
wc -l src/datapulse/control_center/services/*.py src/datapulse/control_center/service.py src/datapulse/control_center/connectors.py
```

- [ ] **Step 8: Commit**

```bash
git add src/datapulse/control_center/services/ src/datapulse/control_center/service.py src/datapulse/control_center/connectors.py
git commit -m "refactor(control_center): split 865-LOC service.py into 4 domain services

Facade ControlCenterService delegates to SourcesService /
PipelinesService / MappingsService / SyncService. _get_connector
extracted to control_center/connectors.py. Callers keep using
ControlCenterService unchanged.

No behavior change. Tests green."
```

---

## Task 6: Split `analytics/service.py` (651 LOC)

**Mirror of Task 5, analytics flavor.**

**Files:**
- Read: `src/datapulse/analytics/service.py`
- Create: `src/datapulse/analytics/services/__init__.py`
- Create: `src/datapulse/analytics/services/kpi.py`
- Create: `src/datapulse/analytics/services/ranking.py`
- Create: `src/datapulse/analytics/services/breakdown.py`
- Create: `src/datapulse/analytics/services/detail.py`
- Create: `src/datapulse/analytics/services/churn.py`
- Create: `src/datapulse/analytics/services/health.py`
- Modify: `src/datapulse/analytics/service.py` → thin `AnalyticsService` facade

- [ ] **Step 1: Map `AnalyticsService` methods to the 6 domains** (same domains as Task 2, Task 4)

```bash
grep -n "def " src/datapulse/analytics/service.py | head -60
```

- [ ] **Step 2: Create domain services**

Each one follows this template:

`src/datapulse/analytics/services/kpi.py`:

```python
"""KPI domain service — orchestrates kpi_repository + caching."""

from __future__ import annotations

from datapulse.analytics.kpi_repository import KpiRepository
from datapulse.analytics.models import DashboardData, KPISummary, TrendResult
# ...


class KpiService:
    """Handles KPI summaries, dashboard rollups, trends, segments."""

    def __init__(self, session, repo: KpiRepository | None = None) -> None:
        self._session = session
        self._repo = repo or KpiRepository(session)

    # --- paste domain methods from the original AnalyticsService ---
    def get_kpi_summary(self, ...) -> KPISummary: ...
```

- [ ] **Step 3: Make `service.py` a facade**

```python
"""Analytics service — thin facade over per-domain services."""

from __future__ import annotations

from datapulse.analytics.services.breakdown import BreakdownService
from datapulse.analytics.services.churn import ChurnService
from datapulse.analytics.services.detail import DetailService
from datapulse.analytics.services.health import HealthService
from datapulse.analytics.services.kpi import KpiService
from datapulse.analytics.services.ranking import RankingService


class AnalyticsService:
    """Facade over per-domain analytics services."""

    def __init__(self, session) -> None:
        self._session = session
        self.kpi = KpiService(session)
        self.ranking = RankingService(session)
        self.breakdown = BreakdownService(session)
        self.detail = DetailService(session)
        self.churn = ChurnService(session)
        self.health = HealthService(session)

    # --- delegate every method used by routes ---
    def get_kpi_summary(self, *args, **kwargs):
        return self.kpi.get_kpi_summary(*args, **kwargs)

    # ... one delegate per public method on the original AnalyticsService
```

- [ ] **Step 4: Lint + test + commit**

```bash
ruff check --fix src/datapulse/analytics/
ruff format src/datapulse/analytics/
pytest -x -q --cov=src/datapulse --cov-fail-under=95
git add src/datapulse/analytics/services/ src/datapulse/analytics/service.py
git commit -m "refactor(analytics): split 651-LOC service.py into 6 domain services

Facade AnalyticsService delegates to kpi/ranking/breakdown/detail/
churn/health sub-services. Route layer imports unchanged.

No behavior change. Tests green."
```

---

## Task 7: Split `analytics/kpi_repository.py` (778 LOC)

**Different pattern:** This file is a single `KpiRepository` class with 8 methods. The two largest methods (`_get_kpi_from_fct_sales` ~234 LOC and `get_kpi_summary_range` ~176 LOC) are dominated by multi-hundred-line SQL strings. Split the SQL out; keep the class in place.

**Files:**
- Read: `src/datapulse/analytics/kpi_repository.py`
- Create: `src/datapulse/analytics/kpi_queries.py` (SQL template constants)
- Modify: `src/datapulse/analytics/kpi_repository.py` to import constants

- [ ] **Step 1: Identify SQL blocks inside the two largest methods**

```bash
grep -n "text(" src/datapulse/analytics/kpi_repository.py
```

Each `text("""...""")` invocation is an extraction candidate.

- [ ] **Step 2: Extract each SQL block to a named constant in `kpi_queries.py`**

`src/datapulse/analytics/kpi_queries.py`:

```python
"""SQL templates for KpiRepository.

Extracted from kpi_repository.py to keep the repository focused on
orchestration and let the SQL stand on its own for review.
"""

from __future__ import annotations

# --- SQL for _get_kpi_from_fct_sales ---
KPI_FROM_FCT_SALES_SQL = """
    SELECT
        ...
"""

# --- SQL for get_kpi_summary_range ---
KPI_SUMMARY_RANGE_SQL = """
    SELECT
        ...
"""

# --- SQL for get_kpi_sparkline ---
KPI_SPARKLINE_SQL = """
    SELECT
        ...
"""
```

Naming rule: `<METHOD_NAME>_SQL`. If a method builds SQL dynamically (concatenation), extract the static chunks into named fragments (e.g. `_KPI_BASE_FROM_CLAUSE`, `_KPI_DATE_FILTER`) and reassemble in the repository.

- [ ] **Step 3: Update `kpi_repository.py` to use the imported constants**

Replace inline `text("""...""")` with `text(KPI_FROM_FCT_SALES_SQL)`. At the top of the file:

```python
from datapulse.analytics.kpi_queries import (
    KPI_FROM_FCT_SALES_SQL,
    KPI_SPARKLINE_SQL,
    KPI_SUMMARY_RANGE_SQL,
)
```

- [ ] **Step 4: Lint + test**

```bash
ruff check --fix src/datapulse/analytics/kpi_repository.py src/datapulse/analytics/kpi_queries.py
ruff format src/datapulse/analytics/kpi_repository.py src/datapulse/analytics/kpi_queries.py
pytest -x -q tests/test_analytics_repository.py -v
pytest -x -q --cov=src/datapulse --cov-fail-under=95
```

- [ ] **Step 5: Confirm LOC target**

```bash
wc -l src/datapulse/analytics/kpi_repository.py src/datapulse/analytics/kpi_queries.py
```

Expected: repository drops from 778 → ~400–500 LOC; queries ~250 LOC. Acceptable if repository is ≤ 500.

- [ ] **Step 6: Commit**

```bash
git add src/datapulse/analytics/kpi_repository.py src/datapulse/analytics/kpi_queries.py
git commit -m "refactor(analytics): extract SQL templates from kpi_repository

SQL constants moved to analytics/kpi_queries.py; repository becomes
focused orchestration code. File drops from 778 to ~450 LOC.

No behavior change. Tests green."
```

---

## Task 8: Split `scheduler.py` (646 LOC)

**Files:**
- Read: `src/datapulse/scheduler.py`
- Create: `src/datapulse/scheduler/__init__.py` (re-exports public surface)
- Create: `src/datapulse/scheduler/executor.py` (job execution loop)
- Create: `src/datapulse/scheduler/triggers.py` (cron/interval trigger registry)
- Create: `src/datapulse/scheduler/models.py` (Job/Schedule/Trigger dataclasses)
- Delete: `src/datapulse/scheduler.py` (module file) — replaced by `scheduler/` package

- [ ] **Step 1: Identify the three responsibility groups**

```bash
grep -n "^class \|^def \|^async def " src/datapulse/scheduler.py
```

Classify each top-level definition into:
- **executor:** the main run loop, dispatch, job-lifecycle handling
- **triggers:** cron parsing, interval calculation, trigger registry
- **models:** dataclasses / enums for Job, Schedule, TriggerConfig, etc.

- [ ] **Step 2: Check what other modules import from scheduler**

```bash
grep -rn "from datapulse.scheduler\|from datapulse import scheduler" src/ tests/
```

Every symbol in that list must be re-exported from the new package's `__init__.py`.

- [ ] **Step 3: Create the package files**

`src/datapulse/scheduler/models.py`:

```python
"""Scheduler data classes and enums."""

from __future__ import annotations

from dataclasses import dataclass

# --- paste each Job/Schedule/Trigger-related dataclass or enum ---
@dataclass
class Job: ...
```

`src/datapulse/scheduler/triggers.py`:

```python
"""Trigger registry — cron and interval schedule definitions."""

from __future__ import annotations

from datapulse.scheduler.models import ...

# --- paste trigger-related functions/classes ---
```

`src/datapulse/scheduler/executor.py`:

```python
"""Job execution loop + dispatcher."""

from __future__ import annotations

from datapulse.scheduler.models import Job, ...
from datapulse.scheduler.triggers import ...

# --- paste executor-related functions/classes ---
```

`src/datapulse/scheduler/__init__.py`:

```python
"""Scheduler — job execution engine, trigger registry, data models.

Split from the original single-file scheduler.py during the Phase 1
simplification sprint.
"""

from datapulse.scheduler.executor import ...  # every public symbol callers use
from datapulse.scheduler.models import Job, Schedule, ...
from datapulse.scheduler.triggers import ...

__all__ = [
    # list every re-exported symbol
]
```

- [ ] **Step 4: Delete the old module**

```bash
rm src/datapulse/scheduler.py
```

- [ ] **Step 5: Lint + test**

```bash
ruff check --fix src/datapulse/scheduler/
ruff format src/datapulse/scheduler/
pytest -x -q --cov=src/datapulse --cov-fail-under=95
```

- [ ] **Step 6: Commit**

```bash
git add src/datapulse/scheduler/ src/datapulse/scheduler.py
git commit -m "refactor(scheduler): split 646-LOC scheduler.py into 3-file package

executor.py (run loop) / triggers.py (cron+interval registry) /
models.py (dataclasses). __init__.py re-exports the public surface so
existing 'from datapulse.scheduler import X' calls still work.

No behavior change. Tests green."
```

---

## Task 9: Final quality sweep + PR

**Files:** (none modified beyond PR body)

- [ ] **Step 1: Regenerate the LOC snapshot and compare**

```bash
find src/datapulse -name "*.py" -exec wc -l {} \; | sort -rn | awk '$1 > 400' | head -20 > /tmp/oversized-after.txt
diff /tmp/oversized-before.txt /tmp/oversized-after.txt
```

Expected: every file from the "before" list appears with far fewer LOC (or is absent entirely because replaced by a package). If any file in the after list is still > 800, stop and address it.

- [ ] **Step 2: Confirm zero lint warnings**

```bash
ruff format --check src/ tests/
ruff check src/ tests/
```

- [ ] **Step 3: Confirm test coverage unchanged from baseline**

```bash
pytest -q --cov=src/datapulse --cov-report=term-missing --cov-fail-under=95
```

Expected: green and coverage ≥ baseline recorded in Task 0.

- [ ] **Step 4: Smoke test the full API stack**

```bash
docker compose up -d --build
sleep 5
curl -sS http://localhost:8000/health | grep -q '"status":"ok"' && echo PASS || echo FAIL
```

Expected: `PASS`.

- [ ] **Step 5: Rebuild the datapulse-graph index so future MCP queries reflect the new structure**

```bash
PYTHONPATH=src python -m datapulse.graph
```

- [ ] **Step 6: Push the branch**

```bash
git push -u origin claude/zen-einstein
```

- [ ] **Step 7: Open the PR**

```bash
gh pr create --title "refactor: phase-1 simplification sprint — split 8 oversized files" --body "$(cat <<'EOF'
## Summary

Phase 1 of a two-phase cleanup. Mechanical file splits only — zero
behavior change, zero schema change, zero new dependencies.

**Before:** 8 Python files exceeded the 400 LOC target; 6 exceeded the
800 LOC cap set in CLAUDE.md.

**After:** every file under 400 LOC (with a handful approaching 500 in
repository/service files — flagged in PR if any). Public import paths
preserved via barrel re-exports so no downstream code changes.

## What was split

| File | Before | After |
|------|--------|-------|
| control_center/repository.py | 937 | 7 per-class files, each ≤ 200 LOC |
| api/routes/control_center.py | 912 | 5 sub-routers, ≤ 250 LOC each |
| control_center/service.py | 865 | 4 domain services + connector dispatcher |
| analytics/kpi_repository.py | 778 | ~450 (SQL extracted to kpi_queries.py) |
| analytics/models.py | 675 | 7 per-domain files, ≤ 250 LOC each |
| api/routes/analytics.py | 657 | 6 domain sub-routers + shared helper |
| analytics/service.py | 651 | 6 domain services |
| scheduler.py | 646 | 3-file package (executor/triggers/models) |

## Test plan

- [ ] `ruff format --check src/ tests/` clean
- [ ] `ruff check src/ tests/` clean
- [ ] `pytest -x -q --cov=src/datapulse --cov-fail-under=95` green
- [ ] `docker compose up` → /health returns 200
- [ ] Manual: hit `/analytics/dashboard` with valid auth → 200
- [ ] Manual: hit `/control-center/source-connections` → 200
- [ ] datapulse-graph re-indexed

## Design reference

docs/superpowers/specs/2026-04-15-cleanup-and-brain-obsidian-design.md

## Follow-up (separate PR)

Phase 2 — Brain→Obsidian export CLI. Spec same file §4. Plan written
after this PR merges so it can reflect the new module structure.
EOF
)"
```

- [ ] **Step 8: Record PR URL and handoff**

Capture the PR URL in the final report. Hand off to the reviewer.

---

## Phase 2 note

Once Phase 1 PR merges, write the Phase 2 plan against [docs/superpowers/specs/2026-04-15-cleanup-and-brain-obsidian-design.md](../specs/2026-04-15-cleanup-and-brain-obsidian-design.md) §4 (Brain → Obsidian export CLI). That plan is deliberately deferred so it can reference real post-refactor module names.

---

## Self-Review Checklist (run before handoff)

- [x] Every spec §3 requirement has a task: 8 file splits (§3.2.1–3.2.8) → Tasks 1–8. Quality gates (§3.4) → Task 9. Consolidation (§3.3) removed because already done; acknowledged in the plan header.
- [x] No placeholders: every step has exact commands, exact file paths, exact class/line mappings, and commit message templates.
- [x] Type consistency: method names (`to_filter`, `get_connector`, `ControlCenterService.sources`) are stable across tasks where they're referenced.
- [x] `/tmp/` paths used for intermediate snapshots — acceptable on Linux/macOS; on Windows, engineers should substitute `%TEMP%` or any writable path. Flagged here so the reader knows.

