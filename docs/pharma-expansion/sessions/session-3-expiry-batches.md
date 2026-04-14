# Session 3: Expiry & Batch Tracking — dim_batch, FEFO, Alerts

## Context Brief

**DataPulse** is a pharma SaaS with medallion architecture. Python 3.11 / FastAPI / PostgreSQL 16 / dbt-core.

**What already exists**:
- Session 1: `bronze.batches` table (migration 052) with columns: tenant_id, drug_code, site_code, batch_number, expiry_date, initial_quantity, current_quantity, unit_cost, status ('active'|'near_expiry'|'expired'|'quarantined'|'written_off'). RLS enabled. Bronze view `bronze_batches.sql` and source definition exist.
- Session 2: `fct_stock_movements` (UNION of receipts + adjustments + dispenses + returns), `agg_stock_levels` (current stock per drug/site), `src/datapulse/inventory/` module with 10 API endpoints
- Existing `dim_product` (17.8k drugs) with drug_code + tenant_id key, `dim_site` (2 sites)
- `feat_product_lifecycle` — Growth/Mature/Decline/Dormant classification
- Billing `PlanLimits` already has `expiry_tracking: bool` field

**Goal**: Build batch/lot dimension, expiry alert features, FEFO enforcement, and full Expiry API with 8 endpoints.

---

## Task List

### 1. Create Batches Loader

#### `src/datapulse/bronze/batches_column_map.py`
```python
COLUMN_MAP: dict[str, str] = {
    "Drug Code": "drug_code",
    "Site Code": "site_code",
    "Batch Number": "batch_number",
    "Expiry Date": "expiry_date",
    "Initial Quantity": "initial_quantity",
    "Current Quantity": "current_quantity",
    "Unit Cost": "unit_cost",
    "Status": "status",
    "Notes": "notes",
}
```

#### `src/datapulse/bronze/batches_loader.py`
`ExcelBatchesLoader(BronzeLoader)`:
- Target: `bronze.batches`
- validate: check drug_code, batch_number, expiry_date not null
- Register in `registry.py`

---

### 2. Create dbt Models

#### `dbt/models/staging/stg_batches.sql`
```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', 'drug_code', 'site_code', 'batch_number'],
        schema='staging',
        post_hook=[ /* standard RLS post_hook */ ]
    )
}}

WITH ranked AS (
    SELECT
        tenant_id,
        TRIM(drug_code) AS drug_code,
        TRIM(site_code) AS site_code,
        TRIM(batch_number) AS batch_number,
        expiry_date,
        ROUND(initial_quantity, 4) AS initial_quantity,
        ROUND(current_quantity, 4) AS current_quantity,
        ROUND(unit_cost, 4) AS unit_cost,
        COALESCE(NULLIF(TRIM(status), ''), 'active') AS status,
        source_file,
        loaded_at,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, drug_code, site_code, batch_number
            ORDER BY loaded_at DESC
        ) AS rn
    FROM {{ ref('bronze_batches') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) - INTERVAL '3 days' FROM {{ this }})
    {% endif %}
)
SELECT * FROM ranked WHERE rn = 1
```

#### `dbt/models/marts/dims/dim_batch.sql`
Follow `dim_product.sql` pattern exactly:
```sql
{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'batch_key'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            /* standard RLS + indexes */
            "CREATE INDEX IF NOT EXISTS idx_dim_batch_drug_code_tenant ON {{ this }} (drug_code, tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_dim_batch_expiry ON {{ this }} (expiry_date)",
            "CREATE INDEX IF NOT EXISTS idx_dim_batch_status ON {{ this }} (status)"
        ]
    )
}}

-- Batch dimension: one row per unique batch per drug per site
-- SCD Type 1: latest attributes win
-- batch_key = deterministic MD5 surrogate

WITH ranked AS (
    SELECT
        tenant_id,
        drug_code,
        site_code,
        batch_number,
        expiry_date,
        initial_quantity,
        current_quantity,
        unit_cost,
        status,
        -- Derived: days until expiry
        (expiry_date - CURRENT_DATE) AS days_to_expiry,
        CASE
            WHEN status IN ('expired', 'written_off', 'quarantined') THEN status
            WHEN expiry_date < CURRENT_DATE THEN 'expired'
            WHEN expiry_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'near_expiry'
            ELSE 'active'
        END AS computed_status,
        loaded_at,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, drug_code, site_code, batch_number
            ORDER BY loaded_at DESC
        ) AS rn
    FROM {{ ref('stg_batches') }}
),

final AS (
    SELECT
        ABS(('x' || LEFT(MD5(
            r.tenant_id::TEXT || '|' || r.drug_code || '|' || r.site_code || '|' || r.batch_number
        ), 8))::BIT(32)::INT) AS batch_key,
        r.*
    FROM ranked r
    WHERE r.rn = 1
)

SELECT * FROM final

{% if not is_incremental() %}
UNION ALL
-- Unknown batch row
SELECT
    -1 AS batch_key,
    t.tenant_id,
    '__UNKNOWN__' AS drug_code,
    '__UNKNOWN__' AS site_code,
    '__UNKNOWN__' AS batch_number,
    NULL AS expiry_date,
    0 AS initial_quantity,
    0 AS current_quantity,
    NULL AS unit_cost,
    'active' AS status,
    0 AS days_to_expiry,
    'active' AS computed_status,
    now() AS loaded_at,
    1 AS rn
FROM (SELECT DISTINCT tenant_id FROM {{ ref('stg_batches') }}) t
{% endif %}
```

#### `dbt/models/marts/facts/fct_batch_status.sql`
Batch lifecycle events — tracks status changes over time:
- Grain: one status event per batch
- Joins to dim_batch, dim_product, dim_site

#### `dbt/models/marts/aggs/agg_expiry_summary.sql`
```sql
-- Grain: one row per (tenant_id, site_key, expiry_bucket)
-- Counts batches by expiry status per site
SELECT
    b.tenant_id,
    s.site_key, s.site_code, s.site_name,
    b.computed_status AS expiry_bucket,
    COUNT(*) AS batch_count,
    SUM(b.current_quantity) AS total_quantity,
    SUM(b.current_quantity * COALESCE(b.unit_cost, 0)) AS total_value
FROM {{ ref('dim_batch') }} b
INNER JOIN {{ ref('dim_site') }} s ON b.site_code = s.site_code AND b.tenant_id = s.tenant_id
WHERE b.batch_key != -1
GROUP BY 1,2,3,4,5
```

#### `dbt/models/marts/features/feat_expiry_alerts.sql`
```sql
-- Batches expiring within 30, 60, 90 days
-- Grain: one row per batch with alert level
SELECT
    b.tenant_id,
    b.batch_key,
    b.drug_code,
    p.drug_name, p.drug_brand,
    b.site_code,
    b.batch_number,
    b.expiry_date,
    b.current_quantity,
    b.days_to_expiry,
    CASE
        WHEN b.days_to_expiry <= 0 THEN 'expired'
        WHEN b.days_to_expiry <= 30 THEN 'critical'
        WHEN b.days_to_expiry <= 60 THEN 'warning'
        WHEN b.days_to_expiry <= 90 THEN 'caution'
        ELSE 'safe'
    END AS alert_level
FROM {{ ref('dim_batch') }} b
INNER JOIN {{ ref('dim_product') }} p ON b.drug_code = p.drug_code AND b.tenant_id = p.tenant_id
WHERE b.batch_key != -1 AND b.current_quantity > 0
```

Create schema YAML files for all new models.

---

### 3. Create FEFO Module

#### `src/datapulse/expiry/fefo.py`
First Expiry First Out batch selection:
```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class BatchSelection:
    batch_number: str
    expiry_date: date
    available_quantity: Decimal
    allocated_quantity: Decimal

def select_batches_fefo(
    available_batches: list[dict],  # sorted by expiry_date ASC
    required_quantity: Decimal,
) -> tuple[list[BatchSelection], Decimal]:
    """Select batches using FEFO (First Expiry First Out).

    Returns (selected_batches, remaining_unfulfilled_quantity).
    """
    selected: list[BatchSelection] = []
    remaining = required_quantity

    for batch in sorted(available_batches, key=lambda b: b["expiry_date"]):
        if remaining <= 0:
            break
        available = Decimal(str(batch["current_quantity"]))
        if available <= 0:
            continue
        allocated = min(available, remaining)
        selected.append(BatchSelection(
            batch_number=batch["batch_number"],
            expiry_date=batch["expiry_date"],
            available_quantity=available,
            allocated_quantity=allocated,
        ))
        remaining -= allocated

    return selected, max(remaining, Decimal("0"))
```

---

### 4. Create Expiry Python Module

#### `src/datapulse/expiry/__init__.py`
Empty.

#### `src/datapulse/expiry/models.py`
```python
class BatchInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    batch_key: int
    drug_code: str
    drug_name: str
    site_code: str
    batch_number: str
    expiry_date: date
    current_quantity: JsonDecimal
    days_to_expiry: int
    alert_level: str  # expired|critical|warning|caution|safe

class ExpiryAlert(BaseModel):
    model_config = ConfigDict(frozen=True)
    drug_code: str
    drug_name: str
    batch_number: str
    expiry_date: date
    current_quantity: JsonDecimal
    days_to_expiry: int
    alert_level: str

class ExpirySummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    site_code: str
    site_name: str
    expired_count: int
    critical_count: int
    warning_count: int
    caution_count: int
    total_expired_value: JsonDecimal

class QuarantineRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    drug_code: str
    site_code: str
    batch_number: str
    reason: str

class WriteOffRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    drug_code: str
    site_code: str
    batch_number: str
    reason: str
    quantity: JsonDecimal

class ExpiryCalendarDay(BaseModel):
    model_config = ConfigDict(frozen=True)
    date: date
    batch_count: int
    total_quantity: JsonDecimal
    alert_level: str
```

#### `src/datapulse/expiry/repository.py`
Methods: `get_batches(filters)`, `get_batches_by_drug(drug_code)`, `get_near_expiry(days_threshold)`, `get_expired()`, `quarantine_batch(request)`, `write_off_batch(request)`, `get_expiry_calendar(start_date, end_date)`, `get_expiry_summary()`

#### `src/datapulse/expiry/service.py`
- `ExpiryService(repo, notification_svc)`
- Quarantine: update batch status, create stock adjustment (type='write_off' negative qty)
- Write-off: update batch status + write_off_date, create stock adjustment
- Notifications: create alert for near-expiry batches

---

### 5. Create API Routes

#### `src/datapulse/api/routes/expiry.py`
8 endpoints. All gated by `limits.expiry_tracking` and `require_permission("expiry:read"/"expiry:write")`.

---

### 6. Wire Dependencies

- Add `get_expiry_service()` to `deps.py`
- Register router in `app.py` (behind `feature_platform`)

---

### 7. Write Tests

- `tests/test_fefo.py` — FEFO algorithm: single batch, multi-batch, insufficient stock, empty batches, expired-first selection
- `tests/test_expiry_models.py`
- `tests/test_expiry_repository.py`
- `tests/test_expiry_service.py` — quarantine/write-off flow, notification triggers
- `tests/test_expiry_endpoints.py`
- `tests/test_batches_loader.py`

---

## Verification Commands

```bash
pytest tests/test_expiry_*.py tests/test_fefo.py tests/test_batches_loader.py -v
cd dbt && dbt compile --select stg_batches dim_batch fct_batch_status agg_expiry_summary feat_expiry_alerts
pytest tests/ -x --timeout=120
ruff format --check src/ tests/
ruff check src/ tests/
```

## Exit Criteria

- [ ] `dim_batch` generates correct MD5 surrogate keys
- [ ] `dim_batch` has -1 Unknown row on full refresh
- [ ] `feat_expiry_alerts` classifies batches into expired/critical/warning/caution/safe
- [ ] FEFO algorithm selects earliest-expiry batch with sufficient quantity
- [ ] FEFO handles partial fulfillment (multiple batches needed)
- [ ] Quarantine endpoint updates batch status + creates stock adjustment
- [ ] Write-off endpoint records write_off_date and reason
- [ ] Expiry calendar returns day-by-day expiry counts
- [ ] Plan gating returns 403 for starter plan
- [ ] RBAC permission `expiry:read`/`expiry:write` enforced
- [ ] 95%+ coverage on new code
- [ ] All existing tests pass
