# Session 5: Dispensing Analytics — Derived Features, Stockout Risk, Reorder Alerts

## Context Brief

**DataPulse** is a pharma SaaS with medallion architecture. Python 3.11 / FastAPI / PostgreSQL 16 / dbt-core.

**What already exists**:
- Session 2: `agg_stock_levels` (current stock per drug/site), `agg_sales_daily` (existing — daily qty + revenue per product), `fct_stock_movements`
- Session 3: `dim_batch`, `feat_expiry_alerts`
- Session 1: `public.reorder_config` table (min_stock, reorder_point, max_stock, reorder_lead_days per drug/site)
- Existing: `feat_product_lifecycle` — Growth/Mature/Decline/Dormant per product (QoQ analysis)
- Existing: `agg_sales_daily` with columns: `tenant_id, product_key, site_key, date_key, year, month, day, daily_quantity, daily_sales`
- Billing `PlanLimits` has `dispensing_analytics: bool` field

**Goal**: Build all derived dispensing analytics — dispense rate, days of stock, product velocity, stockout risk, reorder alerts — plus the reorder config CRUD API. These are mostly dbt feature models reading from existing aggs. Also 5 new API endpoints.

**This is Session 5 of 8.** Depends on Sessions 2 + 3.

---

## Task List

### 1. Create dbt Feature Models (5 models)

#### `dbt/models/marts/features/feat_dispense_rate.sql`
```sql
{{
    config(
        materialized='table',
        schema='marts',
        post_hook=[ /* standard RLS post_hook + indexes */ ]
    )
}}

-- Dispense rate: average quantity dispensed per day per product per site
-- Uses last 90 days of agg_sales_daily for smoothing
-- Grain: one row per (tenant_id, product_key, site_key)

WITH daily AS (
    SELECT
        tenant_id, product_key, site_key,
        daily_quantity,
        date_key
    FROM {{ ref('agg_sales_daily') }}
    WHERE date_key >= (
        SELECT MAX(date_key) - 90  -- last 90 days
        FROM {{ ref('agg_sales_daily') }}
    )
),

rates AS (
    SELECT
        tenant_id, product_key, site_key,
        COUNT(*) AS active_days,
        SUM(daily_quantity) AS total_dispensed_90d,
        ROUND(SUM(daily_quantity) / NULLIF(COUNT(*), 0), 4) AS avg_daily_dispense,
        ROUND(SUM(daily_quantity) / NULLIF(COUNT(*) / 7.0, 0), 4) AS avg_weekly_dispense,
        ROUND(SUM(daily_quantity) / NULLIF(COUNT(*) / 30.0, 0), 4) AS avg_monthly_dispense,
        MAX(date_key) AS last_dispense_date_key
    FROM daily
    GROUP BY 1,2,3
)

SELECT
    r.*,
    p.drug_code, p.drug_name, p.drug_brand,
    s.site_code, s.site_name
FROM rates r
INNER JOIN {{ ref('dim_product') }} p ON r.product_key = p.product_key AND r.tenant_id = p.tenant_id
INNER JOIN {{ ref('dim_site') }} s ON r.site_key = s.site_key AND r.tenant_id = s.tenant_id
```

#### `dbt/models/marts/features/feat_days_of_stock.sql`
```sql
-- Days of stock remaining = current_stock / avg_daily_dispense
-- Grain: one row per (tenant_id, product_key, site_key)

SELECT
    sl.tenant_id,
    sl.product_key,
    sl.site_key,
    sl.drug_code, sl.drug_name,
    sl.site_code, sl.site_name,
    sl.current_quantity,
    dr.avg_daily_dispense,
    CASE
        WHEN dr.avg_daily_dispense IS NULL OR dr.avg_daily_dispense = 0 THEN NULL
        ELSE ROUND(sl.current_quantity / dr.avg_daily_dispense, 1)
    END AS days_of_stock,
    dr.avg_weekly_dispense,
    dr.avg_monthly_dispense,
    dr.last_dispense_date_key
FROM {{ ref('agg_stock_levels') }} sl
LEFT JOIN {{ ref('feat_dispense_rate') }} dr
    ON sl.product_key = dr.product_key
    AND sl.site_key = dr.site_key
    AND sl.tenant_id = dr.tenant_id
```

#### `dbt/models/marts/features/feat_product_velocity.sql`
```sql
-- Extends feat_product_lifecycle with dispense velocity classification
-- Fast/Slow/Dead mover based on avg_daily_dispense relative to category average
-- Grain: one row per (tenant_id, product_key)

WITH category_avg AS (
    SELECT
        dr.tenant_id,
        p.drug_category,
        AVG(dr.avg_daily_dispense) AS category_avg_daily
    FROM {{ ref('feat_dispense_rate') }} dr
    INNER JOIN {{ ref('dim_product') }} p ON dr.product_key = p.product_key AND dr.tenant_id = p.tenant_id
    GROUP BY 1,2
)

SELECT
    dr.tenant_id,
    dr.product_key,
    dr.drug_code, dr.drug_name, dr.drug_brand,
    p.drug_category,
    lc.lifecycle_stage,  -- from existing feat_product_lifecycle
    dr.avg_daily_dispense,
    ca.category_avg_daily,
    CASE
        WHEN dr.avg_daily_dispense >= ca.category_avg_daily * 1.5 THEN 'fast_mover'
        WHEN dr.avg_daily_dispense >= ca.category_avg_daily * 0.5 THEN 'normal_mover'
        WHEN dr.avg_daily_dispense > 0 THEN 'slow_mover'
        ELSE 'dead_stock'
    END AS velocity_class
FROM {{ ref('feat_dispense_rate') }} dr
INNER JOIN {{ ref('dim_product') }} p ON dr.product_key = p.product_key AND dr.tenant_id = p.tenant_id
LEFT JOIN {{ ref('feat_product_lifecycle') }} lc ON dr.product_key = lc.product_key AND dr.tenant_id = lc.tenant_id
LEFT JOIN category_avg ca ON dr.tenant_id = ca.tenant_id AND p.drug_category = ca.drug_category
```

#### `dbt/models/marts/features/feat_stockout_risk.sql`
```sql
-- Products where days_of_stock < reorder_lead_time
-- Uses reorder_config (application table) as a dbt source
-- Grain: one row per (tenant_id, product_key, site_key) at risk

SELECT
    dos.tenant_id,
    dos.product_key, dos.site_key,
    dos.drug_code, dos.drug_name,
    dos.site_code, dos.site_name,
    dos.current_quantity,
    dos.days_of_stock,
    dos.avg_daily_dispense,
    rc.reorder_point,
    rc.reorder_lead_days,
    rc.min_stock,
    CASE
        WHEN dos.current_quantity <= 0 THEN 'stockout'
        WHEN dos.days_of_stock IS NOT NULL AND dos.days_of_stock < rc.reorder_lead_days THEN 'critical'
        WHEN dos.current_quantity <= rc.reorder_point THEN 'at_risk'
        ELSE 'safe'
    END AS risk_level,
    -- Suggested reorder quantity
    GREATEST(rc.reorder_point - dos.current_quantity, 0) AS suggested_reorder_qty
FROM {{ ref('feat_days_of_stock') }} dos
INNER JOIN {{ source('public', 'reorder_config') }} rc
    ON dos.drug_code = rc.drug_code
    AND dos.site_code = rc.site_code
    AND dos.tenant_id = rc.tenant_id
    AND rc.is_active = true
WHERE dos.current_quantity <= rc.reorder_point OR dos.days_of_stock < rc.reorder_lead_days
```

Note: `reorder_config` is an application table, not dbt-managed. Add it as a dbt source:
```yaml
# In _bronze__inventory_sources.yml or a new _public__sources.yml
sources:
  - name: public
    schema: public
    tables:
      - name: reorder_config
```

#### `dbt/models/marts/features/feat_reorder_alerts.sql`
```sql
-- Active reorder alerts for dashboard display
-- Products below reorder_point that need ordering
SELECT
    sr.tenant_id,
    sr.product_key, sr.site_key,
    sr.drug_code, sr.drug_name,
    sr.site_code, sr.site_name,
    sr.current_quantity,
    sr.reorder_point,
    sr.min_stock,
    sr.risk_level,
    sr.suggested_reorder_qty,
    sr.days_of_stock,
    sr.avg_daily_dispense
FROM {{ ref('feat_stockout_risk') }} sr
WHERE sr.risk_level IN ('stockout', 'critical', 'at_risk')
ORDER BY
    CASE sr.risk_level
        WHEN 'stockout' THEN 1
        WHEN 'critical' THEN 2
        WHEN 'at_risk' THEN 3
    END,
    sr.current_quantity ASC
```

Create schema YAML: `dbt/models/marts/features/_features__dispensing_schema.yml`

---

### 2. Create Dispensing Python Module

#### `src/datapulse/dispensing/__init__.py`
Empty.

#### `src/datapulse/dispensing/models.py`
```python
class DispenseRate(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    site_code: str
    site_name: str
    avg_daily_dispense: JsonDecimal
    avg_weekly_dispense: JsonDecimal
    avg_monthly_dispense: JsonDecimal
    active_days: int
    total_dispensed_90d: JsonDecimal

class DaysOfStock(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_key: int
    drug_code: str
    drug_name: str
    site_code: str
    site_name: str
    current_quantity: JsonDecimal
    days_of_stock: JsonDecimal | None  # None if no dispense history
    avg_daily_dispense: JsonDecimal

class VelocityClassification(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    drug_category: str
    lifecycle_stage: str | None
    velocity_class: str  # fast_mover|normal_mover|slow_mover|dead_stock
    avg_daily_dispense: JsonDecimal

class StockoutRisk(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_key: int
    drug_code: str
    drug_name: str
    site_code: str
    site_name: str
    current_quantity: JsonDecimal
    days_of_stock: JsonDecimal | None
    risk_level: str  # stockout|critical|at_risk|safe
    suggested_reorder_qty: JsonDecimal

class ReconciliationEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_key: int
    drug_code: str
    drug_name: str
    site_code: str
    count_date: date
    counted_quantity: JsonDecimal
    calculated_quantity: JsonDecimal
    variance: JsonDecimal
    variance_pct: JsonDecimal | None
```

#### `src/datapulse/dispensing/repository.py`
Queries against the feature tables:
- `get_dispense_rates(filters)` -> `feat_dispense_rate`
- `get_days_of_stock(filters)` -> `feat_days_of_stock`
- `get_velocity(filters)` -> `feat_product_velocity`
- `get_stockout_risk(filters)` -> `feat_stockout_risk`
- `get_reconciliation(filters)` -> `agg_stock_reconciliation`

#### `src/datapulse/dispensing/service.py`
- `DispensingService(repo)` — caching, default filters

---

### 3. Create Reorder Config CRUD

#### `src/datapulse/inventory/reorder_repository.py`
CRUD for `public.reorder_config`:
- `get_config(tenant_id, drug_code, site_code)`
- `list_configs(tenant_id, filters)`
- `create_config(tenant_id, request)` — validate min_stock <= reorder_point <= max_stock
- `update_config(tenant_id, drug_code, site_code, request)` — same validation

#### `src/datapulse/inventory/reorder_service.py`
- `ReorderConfigService(repo)`
- On create/update: if current_stock < new reorder_point, create notification

---

### 4. Create API Routes

#### `src/datapulse/api/routes/dispensing.py` — 5 endpoints
All gated by `limits.dispensing_analytics` and `require_permission("dispensing:read")`:
- GET `/dispensing/rates` — dispense rates
- GET `/dispensing/days-of-stock` — days of stock per product
- GET `/dispensing/velocity` — velocity classification (fast/slow/dead)
- GET `/dispensing/stockout-risk` — products at risk of stockout
- GET `/dispensing/reconciliation` — physical vs calculated stock

Reorder config endpoints go in the existing inventory router (Session 2).

---

### 5. Wire Dependencies

- Add `get_dispensing_service()` to `deps.py`
- Add `get_reorder_config_service()` to `deps.py`
- Register dispensing router in `app.py`

---

### 6. Write Tests

- `tests/test_dispensing_models.py`
- `tests/test_dispensing_repository.py`
- `tests/test_dispensing_service.py`
- `tests/test_dispensing_endpoints.py`
- `tests/test_reorder_config.py` — CRUD + validation (min <= reorder <= max)

---

## Verification Commands

```bash
pytest tests/test_dispensing_*.py tests/test_reorder_config.py -v
cd dbt && dbt compile --select feat_dispense_rate feat_days_of_stock feat_product_velocity feat_stockout_risk feat_reorder_alerts
pytest tests/ -x --timeout=120
ruff format --check src/ tests/
ruff check src/ tests/
```

## Exit Criteria

- [ ] `feat_days_of_stock` correctly divides stock by average daily dispense
- [ ] `feat_days_of_stock` returns NULL when no dispense history (not divide-by-zero)
- [ ] `feat_product_velocity` classifies fast/normal/slow/dead relative to category average
- [ ] `feat_stockout_risk` flags products where days_remaining < lead_time
- [ ] `feat_reorder_alerts` only includes stockout/critical/at_risk products
- [ ] Reorder config CRUD validates min_stock <= reorder_point <= max_stock
- [ ] All endpoints gated by plan + permissions
- [ ] 95%+ coverage on new code
- [ ] All existing tests pass
