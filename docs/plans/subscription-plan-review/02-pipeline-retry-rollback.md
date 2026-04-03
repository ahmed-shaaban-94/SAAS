# Track 2 — Pipeline Retry & Rollback

> **Status**: PLANNED
> **Priority**: HIGH
> **Current State**: Single-attempt execution, no retry logic, no rollback mechanism (except forecasting stage)

---

## Objective

Implement **retry with exponential backoff** for transient failures, **stage-level rollback** for data consistency, and **partial re-execution** so failed pipelines can resume from the last successful stage — not restart from scratch.

---

## Why This Matters

- Every production data pipeline needs retry logic — transient DB/network failures are inevitable
- Without rollback, a failed dbt run leaves the database in an inconsistent state
- "How do you handle pipeline failures?" is a top-3 data engineering interview question
- Demonstrates understanding of distributed systems patterns (saga, checkpoint, idempotency)

---

## Scope

- Retry decorator with configurable exponential backoff
- Stage-level checkpoint system (resume from last success)
- Bronze rollback (DELETE inserted rows by run_id)
- dbt rollback (transaction-wrapped runs with savepoints)
- Dead letter queue for permanently failed runs
- Pipeline run state machine (pending → running → stage_X → completed/failed/retrying)

---

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| Retry decorator | `@with_retry(max_attempts, base_delay, backoff_factor, retryable_exceptions)` |
| Checkpoint system | Persist last successful stage in `pipeline_runs.metadata` JSONB |
| Resume endpoint | `POST /api/v1/pipeline/runs/{id}/resume` — restart from last checkpoint |
| Bronze rollback | DELETE rows WHERE `_pipeline_run_id = ?` on failure |
| dbt rollback | Wrapped execution with pre/post snapshot comparison |
| State machine | Enum-based stage tracking with transition validation |
| Dead letter table | `pipeline_dead_letters` for runs that exhaust retries |
| Tests | 30+ tests covering retry, rollback, resume, dead letter scenarios |

---

## Technical Details

### Retry Decorator

```python
# src/datapulse/pipeline/retry.py

import asyncio
import functools
from typing import Type
import structlog

logger = structlog.get_logger()

TRANSIENT_EXCEPTIONS: tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,                    # Network I/O errors
)


class RetryExhaustedError(Exception):
    """All retry attempts failed."""
    def __init__(self, stage: str, attempts: int, last_error: Exception):
        self.stage = stage
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Stage '{stage}' failed after {attempts} attempts: {last_error}")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
    retryable: tuple[Type[Exception], ...] = TRANSIENT_EXCEPTIONS,
):
    """Retry decorator with exponential backoff for pipeline stages."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable as exc:
                    last_error = exc
                    if attempt < max_attempts:
                        delay = base_delay * (backoff_factor ** (attempt - 1))
                        logger.warning(
                            "stage_retry",
                            stage=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            delay=delay,
                            error=str(exc),
                        )
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(
                            "stage_retry_exhausted",
                            stage=func.__name__,
                            attempts=max_attempts,
                            error=str(exc),
                        )
            raise RetryExhaustedError(func.__name__, max_attempts, last_error)
        return wrapper
    return decorator
```

### Pipeline State Machine

```python
# src/datapulse/pipeline/state_machine.py

from enum import Enum


class PipelineStage(str, Enum):
    PENDING = "pending"
    BRONZE = "bronze"
    QUALITY_BRONZE = "quality_bronze"
    SILVER = "silver"
    QUALITY_SILVER = "quality_silver"
    GOLD = "gold"
    QUALITY_GOLD = "quality_gold"
    FORECASTING = "forecasting"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# Valid stage transitions
TRANSITIONS: dict[PipelineStage, set[PipelineStage]] = {
    PipelineStage.PENDING:        {PipelineStage.BRONZE, PipelineStage.FAILED},
    PipelineStage.BRONZE:         {PipelineStage.QUALITY_BRONZE, PipelineStage.FAILED, PipelineStage.RETRYING},
    PipelineStage.QUALITY_BRONZE: {PipelineStage.SILVER, PipelineStage.FAILED},
    PipelineStage.SILVER:         {PipelineStage.QUALITY_SILVER, PipelineStage.FAILED, PipelineStage.RETRYING},
    PipelineStage.QUALITY_SILVER: {PipelineStage.GOLD, PipelineStage.FAILED},
    PipelineStage.GOLD:           {PipelineStage.QUALITY_GOLD, PipelineStage.FAILED, PipelineStage.RETRYING},
    PipelineStage.QUALITY_GOLD:   {PipelineStage.FORECASTING, PipelineStage.COMPLETED, PipelineStage.FAILED},
    PipelineStage.FORECASTING:    {PipelineStage.COMPLETED, PipelineStage.FAILED, PipelineStage.RETRYING},
    PipelineStage.RETRYING:       {PipelineStage.BRONZE, PipelineStage.SILVER, PipelineStage.GOLD, PipelineStage.FORECASTING, PipelineStage.FAILED},
    PipelineStage.FAILED:         {PipelineStage.RETRYING, PipelineStage.PENDING},  # manual retry
    PipelineStage.COMPLETED:      set(),  # terminal state
}


class InvalidTransitionError(Exception):
    pass


def validate_transition(current: PipelineStage, target: PipelineStage) -> None:
    """Raise if the stage transition is not allowed."""
    allowed = TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from {current.value} to {target.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )
```

### Checkpoint System

```python
# Added to pipeline_runs.metadata JSONB:
{
    "checkpoint": {
        "last_successful_stage": "silver",
        "completed_stages": ["bronze", "quality_bronze", "silver", "quality_silver"],
        "stage_timings": {
            "bronze": {"started_at": "...", "completed_at": "...", "duration_s": 45.2},
            "silver": {"started_at": "...", "completed_at": "...", "duration_s": 12.8}
        },
        "retry_history": [
            {"stage": "gold", "attempt": 1, "error": "timeout", "timestamp": "..."},
            {"stage": "gold", "attempt": 2, "error": "timeout", "timestamp": "..."}
        ]
    }
}
```

### Bronze Rollback Strategy

```python
# src/datapulse/pipeline/rollback.py

def rollback_bronze(session: Session, run_id: UUID) -> int:
    """Delete all bronze rows inserted by this pipeline run.

    Requires: bronze.sales._pipeline_run_id column (new).
    Returns: number of rows deleted.
    """
    result = session.execute(
        text("DELETE FROM bronze.sales WHERE _pipeline_run_id = :run_id"),
        {"run_id": str(run_id)},
    )
    session.commit()
    return result.rowcount
```

### dbt Rollback Strategy

```python
def rollback_dbt(session: Session, stage: str) -> None:
    """Rollback dbt models by re-running the previous successful version.

    Strategy: dbt uses CREATE OR REPLACE for views (instant rollback via git)
    and CREATE TABLE AS for tables. For tables, we:
    1. Before run: snapshot row counts per model
    2. After failed run: compare counts
    3. If drift detected: re-run dbt with --full-refresh from last known-good
    """
    pass  # Implementation depends on dbt adapter behavior
```

### Resume Endpoint

```
POST /api/v1/pipeline/runs/{run_id}/resume

Response:
{
    "run_id": "uuid",
    "resumed_from_stage": "silver",
    "skipped_stages": ["bronze", "quality_bronze"],
    "status": "running"
}
```

### Dead Letter Table

```sql
CREATE TABLE public.pipeline_dead_letters (
    id              SERIAL PRIMARY KEY,
    pipeline_run_id UUID REFERENCES public.pipeline_runs(id),
    tenant_id       UUID NOT NULL,
    failed_stage    TEXT NOT NULL,
    attempts        INTEGER NOT NULL,
    last_error      TEXT,
    error_details   JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT
);

ALTER TABLE public.pipeline_dead_letters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_dead_letters FORCE ROW LEVEL SECURITY;
```

---

## Module Structure

```
src/datapulse/pipeline/
├── executor.py           # Modified: wrap stages with @with_retry
├── retry.py              # NEW: retry decorator + RetryExhaustedError
├── state_machine.py      # NEW: PipelineStage enum + transition validation
├── rollback.py           # NEW: rollback functions per stage
├── checkpoint.py         # NEW: checkpoint read/write in metadata JSONB
└── dead_letter.py        # NEW: dead letter repository + service

migrations/
└── 008_add_pipeline_retry.sql  # NEW: _pipeline_run_id column, dead_letters table
```

---

## API Endpoints (New/Modified)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/pipeline/runs/{id}/resume` | Resume failed run from last checkpoint |
| GET | `/api/v1/pipeline/dead-letters` | List dead letter entries |
| POST | `/api/v1/pipeline/dead-letters/{id}/resolve` | Mark dead letter as resolved |

---

## Dependencies

- Track 1 (Frontend Testing) — not required but helpful for testing UI changes
- Existing pipeline module (Phase 2.2-2.3)
- Migration system
