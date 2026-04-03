# Track 3 — Quality Gates Enhancement

> **Status**: PLANNED
> **Priority**: HIGH
> **Current State**: 7 hard-coded checks, fixed thresholds, no UI configuration, no historical trending

---

## Objective

Transform quality gates from hard-coded checks into a **configurable rule engine** with UI-managed thresholds, **historical quality trending**, **data profiling**, and **anomaly detection** — making DataPulse a serious data quality platform.

---

## Why This Matters

- Data quality is the #1 concern in enterprise data engineering
- Configurable thresholds show understanding of multi-tenant SaaS patterns
- Quality trending and profiling are Power BI / dbt-adjacent skills employers want
- Anomaly detection (even rule-based) demonstrates analytical thinking

---

## Scope

- Configurable quality rules with per-tenant thresholds
- Quality rules CRUD API + frontend management UI
- Historical quality scorecard (daily quality score trending)
- Data profiling module (distribution, cardinality, outlier detection)
- Quality alerting integration (n8n Slack notifications on gate failure)
- 40+ tests

---

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| Quality rules table | `quality_rules` with configurable thresholds per tenant |
| Rules CRUD API | 4 endpoints: list, create, update, delete rules |
| Rules management UI | Frontend page for managing quality thresholds |
| Quality scorecard | Daily quality score calculation + trending chart |
| Data profiling | Column-level stats: min/max/mean/median/stddev/nulls/cardinality/distribution |
| Anomaly flags | Statistical anomaly detection (z-score > 3σ on key metrics) |
| Quality dashboard | Enhanced pipeline page with quality trends + profiling |
| Tests | 40+ unit/integration tests |

---

## Technical Details

### Quality Rules Table

```sql
CREATE TABLE public.quality_rules (
    id              SERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    check_name      TEXT NOT NULL,          -- row_count, null_rate, schema_drift, etc.
    stage           TEXT NOT NULL,          -- bronze, silver, gold
    enabled         BOOLEAN DEFAULT true,
    severity        TEXT DEFAULT 'warn',    -- error (blocking) or warn (non-blocking)
    config          JSONB NOT NULL,         -- threshold values, column lists, etc.
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, check_name, stage)
);

-- Example configs:
-- null_rate:    {"threshold": 0.05, "columns": ["reference_no", "date", "net_sales"]}
-- row_count:   {"min_rows": 1, "max_drop_pct": 50}
-- schema_drift: {"required_columns": ["reference_no", "date", "net_sales", "quantity"]}
-- financial_signs: {"mismatch_threshold": 0.01}
-- freshness:   {"max_age_hours": 48}
-- custom_sql:  {"query": "SELECT COUNT(*) FROM ... WHERE ...", "expected": "0"}
```

### Configurable Check Engine

```python
# src/datapulse/pipeline/quality_engine.py

class QualityEngine:
    """Executes quality checks using configurable rules instead of hard-coded thresholds."""

    def __init__(self, session: Session, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    def load_rules(self, stage: str) -> list[QualityRule]:
        """Load enabled rules for this tenant + stage. Falls back to defaults."""
        rules = self.session.execute(
            select(QualityRule)
            .where(QualityRule.tenant_id == self.tenant_id)
            .where(QualityRule.stage == stage)
            .where(QualityRule.enabled.is_(True))
        ).scalars().all()

        if not rules:
            return self._default_rules(stage)
        return rules

    def run(self, stage: str, run_id: UUID) -> QualityGateResult:
        """Execute all rules for a stage and return gate result."""
        rules = self.load_rules(stage)
        results = []

        for rule in rules:
            checker = CHECK_REGISTRY[rule.check_name]
            result = checker(self.session, run_id, rule.config)
            results.append(result)

        return QualityGateResult(
            all_passed=all(r.passed for r in results),
            gate_passed=all(r.passed for r in results if r.severity == "error"),
            results=results,
        )


# Check function registry
CHECK_REGISTRY: dict[str, Callable] = {
    "row_count": check_row_count,
    "null_rate": check_null_rate,
    "schema_drift": check_schema_drift,
    "row_delta": check_row_delta,
    "dedup_effective": check_dedup_effective,
    "financial_signs": check_financial_signs,
    "dbt_tests": run_dbt_tests,
    "freshness": check_freshness,          # NEW
    "custom_sql": check_custom_sql,        # NEW
}
```

### Data Profiling Module

```python
# src/datapulse/pipeline/profiler.py

@dataclass(frozen=True)
class ColumnProfile:
    column_name: str
    dtype: str
    total_rows: int
    null_count: int
    null_rate: float
    unique_count: int
    cardinality: float          # unique_count / total_rows
    min_value: str | None
    max_value: str | None
    mean: float | None          # numeric only
    median: float | None        # numeric only
    stddev: float | None        # numeric only
    p25: float | None           # 25th percentile
    p75: float | None           # 75th percentile
    most_common: list[tuple[str, int]]  # top 5 values + counts


@dataclass(frozen=True)
class TableProfile:
    table_name: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    profiled_at: datetime


def profile_table(session: Session, schema: str, table: str) -> TableProfile:
    """Generate statistical profile for a table using SQL aggregations."""
    # Single-pass SQL with PERCENTILE_CONT, COUNT, AVG, STDDEV
    ...
```

### Quality Scorecard

```python
# Daily quality score = (passed_checks / total_checks) * 100

# Stored in quality_checks table, aggregated by:
# - Daily: avg score per day
# - Weekly: trend direction (improving/declining/stable)
# - Monthly: quality SLA compliance (% days above threshold)
```

### Anomaly Detection (Statistical)

```python
# src/datapulse/pipeline/anomaly.py

def detect_anomalies(session: Session, tenant_id: UUID) -> list[Anomaly]:
    """Detect statistical anomalies in daily metrics using z-score method.

    For each metric in metrics_summary:
    1. Calculate rolling 30-day mean and stddev
    2. Compute z-score for latest value
    3. Flag if |z-score| > 3 (3-sigma rule)
    """
    ...
```

### API Endpoints (New)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/pipeline/quality-rules` | List quality rules for tenant |
| POST | `/api/v1/pipeline/quality-rules` | Create new quality rule |
| PUT | `/api/v1/pipeline/quality-rules/{id}` | Update rule thresholds |
| DELETE | `/api/v1/pipeline/quality-rules/{id}` | Disable/delete rule |
| GET | `/api/v1/pipeline/quality-scorecard` | Daily quality scores + trend |
| GET | `/api/v1/pipeline/profile/{stage}` | Data profile for stage table |
| GET | `/api/v1/analytics/anomalies` | Detected anomalies list |

### Frontend Components (New)

| Component | Description |
|-----------|-------------|
| `quality-rules-table.tsx` | CRUD table for managing quality rules |
| `quality-rule-form.tsx` | Form for creating/editing a rule (threshold, severity, columns) |
| `quality-scorecard.tsx` | Line chart showing daily quality score trend |
| `data-profile-card.tsx` | Column profiling stats with distribution mini-charts |
| `anomaly-badge.tsx` | Badge/alert for detected anomalies |

---

## Module Structure

```
src/datapulse/pipeline/
├── quality.py              # Modified: accept config dict instead of hard-coded values
├── quality_engine.py       # NEW: configurable check engine with rule loading
├── quality_rules_repo.py   # NEW: CRUD for quality_rules table
├── profiler.py             # NEW: table/column profiling
├── anomaly.py              # NEW: statistical anomaly detection

frontend/src/
├── components/pipeline/
│   ├── quality-rules-table.tsx   # NEW
│   ├── quality-rule-form.tsx     # NEW
│   ├── quality-scorecard.tsx     # NEW
│   └── data-profile-card.tsx     # NEW

migrations/
└── 009_create_quality_rules.sql  # NEW
```

---

## Dependencies

- Track 2 (Pipeline Retry/Rollback) — quality gate failures can trigger retries
- Existing quality module (Phase 2.5)
- n8n notification workflows (Phase 2.6)
