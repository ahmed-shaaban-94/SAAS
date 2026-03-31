# Data Quality Validation

Data quality framework for the DataPulse medallion pipeline: 7 quality check functions, quality gates, and pipeline integration.

## Current State (DONE)

- **Module**: `src/datapulse/pipeline/quality.py`
- **Service**: `src/datapulse/pipeline/quality_service.py`
- **Repository**: `src/datapulse/pipeline/quality_repository.py`
- **Table**: `public.quality_checks` (with RLS)
- **API**: `GET /api/v1/pipeline/{run_id}/quality`, `POST /api/v1/pipeline/{run_id}/quality-check`
- **Tests**: 79 tests covering quality functions, repository, and service

## The 7 Quality Checks

Each check function returns a `QualityCheckResult` with `passed: bool`, `metric_value: float`, and `details: dict`.

### 1. Row Count Check

**Purpose**: Verify the output row count is within expected bounds.

```python
def check_row_count(actual: int, expected_min: int, expected_max: int) -> QualityCheckResult
```

- **When**: After each pipeline stage (bronze, staging, marts)
- **Pass condition**: `expected_min <= actual <= expected_max`
- **Example**: Bronze load expects 1M-3M rows; staging expects 50-100% of bronze (deduplication)

### 2. Null Rate Check

**Purpose**: Ensure critical columns do not exceed a null threshold.

```python
def check_null_rate(null_count: int, total_count: int, threshold: float) -> QualityCheckResult
```

- **When**: After staging and marts
- **Pass condition**: `null_count / total_count <= threshold`
- **Example**: `reference_no` should have < 1% nulls; `customer_name` should have < 5% nulls

### 3. Schema Drift Check

**Purpose**: Detect unexpected column additions, removals, or type changes.

```python
def check_schema_drift(expected_columns: list[str], actual_columns: list[str]) -> QualityCheckResult
```

- **When**: After bronze load (source schema may change)
- **Pass condition**: Expected columns are a subset of actual columns (new columns are warnings, missing columns fail)

### 4. Duplicate Check

**Purpose**: Detect duplicate rows on a key column.

```python
def check_duplicates(total_count: int, distinct_count: int, threshold: float) -> QualityCheckResult
```

- **When**: After staging (deduplication should have run)
- **Pass condition**: `(total_count - distinct_count) / total_count <= threshold`

### 5. Value Range Check

**Purpose**: Verify numeric values fall within acceptable bounds.

```python
def check_value_range(min_val: float, max_val: float, expected_min: float, expected_max: float) -> QualityCheckResult
```

- **When**: After marts aggregation
- **Pass condition**: `expected_min <= min_val` and `max_val <= expected_max`
- **Example**: `net_sales` should be between -1M and 10M per transaction

### 6. Freshness Check

**Purpose**: Verify data is not stale (most recent record is within expected recency).

```python
def check_freshness(latest_date: datetime, max_age_hours: int) -> QualityCheckResult
```

- **When**: After bronze load
- **Pass condition**: `now() - latest_date <= max_age_hours`

### 7. Referential Integrity Check

**Purpose**: Verify foreign keys resolve to existing dimension records.

```python
def check_referential_integrity(orphan_count: int, total_count: int, threshold: float) -> QualityCheckResult
```

- **When**: After marts fact table build
- **Pass condition**: `orphan_count / total_count <= threshold`
- **Example**: All `fct_sales.customer_key` values should exist in `dim_customer`

## Quality Gate Logic

The quality service orchestrates checks and determines pass/fail:

```
Pipeline Stage Completes
        |
        v
  Run Quality Checks (1-N checks per stage)
        |
        v
  Persist Results to quality_checks table
        |
        v
  Evaluate Gate: ALL checks passed?
       / \
      /   \
   YES     NO
    |       |
    v       v
  Continue  Fail Pipeline
  to next   (mark run as failed,
  stage     log details)
```

### Gate Modes

| Mode | Behaviour |
|------|-----------|
| **Strict** | Any check failure fails the pipeline |
| **Warn** | Failures are logged but pipeline continues |
| **Threshold** | Pipeline fails only if > N checks fail |

## Pipeline Integration

Quality checks run at three points in the pipeline:

| Stage | Checks Run | Gate Mode |
|-------|-----------|-----------|
| After Bronze | row_count, schema_drift, freshness | Strict |
| After Staging (Silver) | row_count, null_rate, duplicates | Strict |
| After Marts (Gold) | row_count, value_range, referential_integrity | Strict |

### n8n Workflow Integration

The `2.3.1_full_pipeline_webhook.json` workflow includes quality gate nodes:

```
Webhook -> Bronze -> QC -> Staging -> QC -> Marts -> QC -> Success
                     |                |              |
                     v                v              v
                  Fail Alert      Fail Alert      Fail Alert
```

## API Endpoints

### Get Quality Results

```bash
# Get all quality check results for a pipeline run
curl http://localhost:8000/api/v1/pipeline/{run_id}/quality
```

Response:

```json
{
  "checks": [
    {
      "id": 1,
      "pipeline_run_id": "uuid",
      "check_name": "row_count",
      "stage": "bronze",
      "passed": true,
      "metric_value": 1134073.0,
      "details": {"expected_min": 1000000, "expected_max": 3000000},
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### Trigger Quality Check

```bash
# Run a specific quality check for a pipeline run
curl -X POST http://localhost:8000/api/v1/pipeline/{run_id}/quality-check \
  -H "Content-Type: application/json" \
  -d '{"check_name": "row_count", "stage": "bronze"}'
```

## Database Schema

```sql
-- public.quality_checks
CREATE TABLE quality_checks (
    id SERIAL PRIMARY KEY,
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id),
    check_name VARCHAR(100) NOT NULL,
    stage VARCHAR(50) NOT NULL,
    passed BOOLEAN NOT NULL,
    metric_value NUMERIC,
    details JSONB,
    tenant_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS enabled
ALTER TABLE quality_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_checks FORCE ROW LEVEL SECURITY;
```

## Recommended Additions (TODO)

### Statistical Checks

- [ ] Standard deviation check -- flag values > 3 sigma from mean
- [ ] Distribution check -- detect skew changes between runs
- [ ] Trend check -- alert when metrics change > X% from previous run

### Historical Comparison

- [ ] Compare current check results against the last N runs
- [ ] Detect gradual degradation trends
- [ ] Store historical baselines per check

### Alert Enrichment

- [ ] Include sample failing rows in quality check details
- [ ] Add remediation suggestions to check results
- [ ] Link to specific dbt test failures when applicable

### Dashboard Integration

- [ ] Display quality check history on the pipeline dashboard
- [ ] Show pass/fail trends over time
- [ ] Quality score metric (% of checks passing over last 30 days)
