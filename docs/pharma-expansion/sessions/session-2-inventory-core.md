# Session 2: Inventory Core — Loaders, Staging, Facts, Aggs, API

## Context Brief

**DataPulse** is a pharma sales analytics SaaS with medallion architecture (bronze->staging->gold). Python 3.11 / FastAPI / PostgreSQL 16 / dbt-core / Polars / Next.js 14.

**What Session 1 built** (already exists in codebase):
- 10 migrations (050-059): `bronze.stock_receipts`, `bronze.stock_adjustments`, `bronze.inventory_counts`, `public.reorder_config`, `bronze.batches`, `bronze.suppliers`, `bronze.purchase_orders`, `bronze.po_lines`, `bronze.pos_transactions` — all with RLS
- `src/datapulse/bronze/base_loader.py` — abstract `BronzeLoader` ABC with template method
- `src/datapulse/bronze/registry.py` — loader registry
- `src/datapulse/billing/plans.py` — updated `PlanLimits` with `inventory_management`, `expiry_tracking`, etc.
- 7 bronze dbt views + source definitions in `dbt/models/bronze/`
- Feature flag: `feature_platform` in config

**Goal of this session**: Build the complete inventory data pipeline — Excel loaders, dbt staging models, the central `fct_stock_movements` fact table, aggregations, and the full Inventory API (Route->Service->Repository) with 10 endpoints.

**This is Session 2 of 8.** Depends on Session 1. Sessions 3 and 4 can run in parallel with this session.

---

## Task List

### 1. Create Column Maps and Loaders (3 pairs)

Each loader follows the existing `bronze/loader.py` pattern. Read that file first to match its structure exactly.

#### `src/datapulse/bronze/receipts_column_map.py`
```python
"""Column mapping for stock receipts Excel import."""

COLUMN_MAP: dict[str, str] = {
    "Receipt Date": "receipt_date",
    "Receipt Reference": "receipt_reference",
    "Drug Code": "drug_code",
    "Site Code": "site_code",
    "Batch Number": "batch_number",
    "Expiry Date": "expiry_date",
    "Quantity": "quantity",
    "Unit Cost": "unit_cost",
    "Supplier Code": "supplier_code",
    "PO Reference": "po_reference",
    "Notes": "notes",
}
```

#### `src/datapulse/bronze/receipts_loader.py`
Concrete `ExcelReceiptsLoader(BronzeLoader)`:
- `get_target_table()` -> `"bronze.stock_receipts"`
- `get_column_map()` -> `COLUMN_MAP` from receipts_column_map
- `get_allowed_columns()` -> frozenset of COLUMN_MAP values + `{"source_file", "loaded_at", "tenant_id"}`
- `discover()` -> find `.xlsx` files in source directory
- `read()` -> read single Excel with `calamine` engine via Polars, add `source_file` column
- `validate()` -> check required columns exist, check drug_code not null
- Template method `run()` from BronzeLoader base handles batch INSERT

Repeat same pattern for:
- `adjustments_column_map.py` + `adjustments_loader.py` -> `bronze.stock_adjustments`
- `counts_column_map.py` + `counts_loader.py` -> `bronze.inventory_counts`

---

### 2. Create dbt Staging Models (3 models)

All staging models follow the `stg_sales.sql` pattern exactly. Read that file for the template.

**Config block** (same for all staging):
```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', '<natural_key_columns>'],
        on_schema_change='sync_all_columns',
        schema='staging',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)"
        ]
    )
}}
```

#### `dbt/models/staging/stg_stock_receipts.sql`
- Source: `{{ ref('bronze_stock_receipts') }}`
- Unique key: `['tenant_id', 'receipt_reference', 'drug_code', 'site_code', 'batch_number']`
- Dedup: ROW_NUMBER() PARTITION BY natural key ORDER BY loaded_at DESC
- Trim text fields, NULLIF empty strings
- Incremental filter: `WHERE loaded_at > (SELECT MAX(loaded_at) - INTERVAL '3 days' FROM {{ this }})`

#### `dbt/models/staging/stg_stock_adjustments.sql`
- Unique key: `['tenant_id', 'drug_code', 'site_code', 'adjustment_date', 'adjustment_type', 'batch_number']`
- Same dedup + cleanup pattern

#### `dbt/models/staging/stg_inventory_counts.sql`
- Unique key: `['tenant_id', 'drug_code', 'site_code', 'count_date', 'batch_number']`
- Same pattern

**Schema**: Create `dbt/models/staging/_staging__inventory_schema.yml` with column descriptions and tests (not_null on drug_code, site_code, tenant_id).

---

### 3. Create Fact Models

#### `dbt/models/marts/facts/fct_stock_movements.sql`
This is the **central inventory fact table** — a UNION of 4 movement types:

```sql
{{
    config(
        materialized='incremental',
        unique_key='movement_key',
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            -- standard RLS post_hook (same as fct_sales)
            -- indexes on: tenant_id, product_key, site_key, movement_date, movement_type
        ]
    )
}}

-- Stock movements fact table
-- Grain: one movement event (receipt, adjustment, dispense, return)
-- UNION of 4 sources into a single event stream

WITH receipts AS (
    SELECT
        tenant_id,
        receipt_date AS movement_date,
        drug_code,
        site_code,
        batch_number,
        'receipt' AS movement_type,
        quantity,           -- positive (incoming)
        unit_cost,
        receipt_reference AS reference,
        loaded_at
    FROM {{ ref('stg_stock_receipts') }}
),

adjustments AS (
    SELECT
        tenant_id,
        adjustment_date AS movement_date,
        drug_code,
        site_code,
        batch_number,
        adjustment_type AS movement_type,
        quantity,           -- positive or negative
        NULL::NUMERIC(18,4) AS unit_cost,
        reason AS reference,
        loaded_at
    FROM {{ ref('stg_stock_adjustments') }}
),

dispenses AS (
    -- Outflow from sales (existing fct_sales)
    SELECT
        f.tenant_id,
        d.full_date AS movement_date,
        p.drug_code,
        s.site_code,
        NULL AS batch_number,
        'dispense' AS movement_type,
        -f.quantity,         -- negative (outgoing)
        NULL::NUMERIC(18,4) AS unit_cost,
        f.invoice_id AS reference,
        f.loaded_at
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    INNER JOIN {{ ref('dim_product') }} p ON f.product_key = p.product_key AND f.tenant_id = p.tenant_id
    INNER JOIN {{ ref('dim_site') }} s ON f.site_key = s.site_key AND f.tenant_id = s.tenant_id
    WHERE f.quantity > 0 AND f.is_return = FALSE
),

returns AS (
    -- Inflow from returns (existing fct_sales with is_return=TRUE)
    SELECT
        f.tenant_id,
        d.full_date AS movement_date,
        p.drug_code,
        s.site_code,
        NULL AS batch_number,
        'return' AS movement_type,
        ABS(f.quantity),     -- positive (incoming)
        NULL::NUMERIC(18,4) AS unit_cost,
        f.invoice_id AS reference,
        f.loaded_at
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    INNER JOIN {{ ref('dim_product') }} p ON f.product_key = p.product_key AND f.tenant_id = p.tenant_id
    INNER JOIN {{ ref('dim_site') }} s ON f.site_key = s.site_key AND f.tenant_id = s.tenant_id
    WHERE f.is_return = TRUE
),

all_movements AS (
    SELECT * FROM receipts
    UNION ALL
    SELECT * FROM adjustments
    UNION ALL
    SELECT * FROM dispenses
    UNION ALL
    SELECT * FROM returns
),

with_keys AS (
    SELECT
        -- Deterministic surrogate key (MD5 of natural key)
        ('x' || LEFT(MD5(
            COALESCE(m.tenant_id::TEXT, '') || '|' ||
            COALESCE(m.movement_date::TEXT, '') || '|' ||
            COALESCE(m.drug_code, '') || '|' ||
            COALESCE(m.site_code, '') || '|' ||
            COALESCE(m.movement_type, '') || '|' ||
            COALESCE(m.reference, '') || '|' ||
            COALESCE(m.batch_number, '') || '|' ||
            COALESCE(m.quantity::TEXT, '')
        ), 16))::BIT(64)::BIGINT AS movement_key,

        m.tenant_id,
        COALESCE(p.product_key, -1) AS product_key,
        COALESCE(s.site_key, -1) AS site_key,
        -- date_key from dim_date
        COALESCE(dd.date_key, -1) AS date_key,
        m.movement_date,
        m.movement_type,
        m.batch_number,
        ROUND(m.quantity, 4) AS quantity,
        ROUND(m.unit_cost, 4) AS unit_cost,
        m.reference,
        m.loaded_at

    FROM all_movements m
    LEFT JOIN {{ ref('dim_product') }} p ON m.drug_code = p.drug_code AND m.tenant_id = p.tenant_id
    LEFT JOIN {{ ref('dim_site') }} s ON m.site_code = s.site_code AND m.tenant_id = s.tenant_id
    LEFT JOIN {{ ref('dim_date') }} dd ON m.movement_date = dd.full_date

    {% if is_incremental() %}
    WHERE m.loaded_at > (SELECT MAX(loaded_at) FROM {{ this }})
    {% endif %}
)

SELECT * FROM with_keys
```

#### `dbt/models/marts/facts/fct_inventory_counts.sql`
- Grain: one physical count per drug/site/batch/date
- Joins to dim_product, dim_site, dim_date
- MD5 surrogate key
- Same RLS post_hook

---

### 4. Create Aggregation Models

#### `dbt/models/marts/aggs/agg_stock_levels.sql`
Current stock per drug per site = SUM of all movements:
```sql
-- Grain: one row per (tenant_id, product_key, site_key)
SELECT
    m.tenant_id,
    m.product_key,
    m.site_key,
    p.drug_code, p.drug_name, p.drug_brand,
    s.site_code, s.site_name,
    SUM(m.quantity) AS current_quantity,
    SUM(CASE WHEN m.movement_type = 'receipt' THEN m.quantity ELSE 0 END) AS total_received,
    SUM(CASE WHEN m.movement_type = 'dispense' THEN ABS(m.quantity) ELSE 0 END) AS total_dispensed,
    SUM(CASE WHEN m.movement_type IN ('damage','shrinkage','write_off') THEN ABS(m.quantity) ELSE 0 END) AS total_wastage,
    MAX(m.movement_date) AS last_movement_date
FROM {{ ref('fct_stock_movements') }} m
INNER JOIN {{ ref('dim_product') }} p ON m.product_key = p.product_key AND m.tenant_id = p.tenant_id
INNER JOIN {{ ref('dim_site') }} s ON m.site_key = s.site_key AND m.tenant_id = s.tenant_id
GROUP BY 1,2,3,4,5,6,7,8
```

#### `dbt/models/marts/aggs/agg_stock_valuation.sql`
Weighted average cost per unit:
```sql
-- Grain: one row per (tenant_id, product_key, site_key)
-- WAC = SUM(receipt_qty * unit_cost) / SUM(receipt_qty)
SELECT
    m.tenant_id, m.product_key, m.site_key,
    SUM(CASE WHEN m.movement_type = 'receipt' AND m.unit_cost IS NOT NULL
        THEN m.quantity * m.unit_cost ELSE 0 END)
    / NULLIF(SUM(CASE WHEN m.movement_type = 'receipt' AND m.unit_cost IS NOT NULL
        THEN m.quantity ELSE 0 END), 0) AS weighted_avg_cost,
    sl.current_quantity,
    ROUND(sl.current_quantity * (weighted_avg_cost), 2) AS stock_value
FROM {{ ref('fct_stock_movements') }} m
INNER JOIN {{ ref('agg_stock_levels') }} sl ON m.product_key = sl.product_key AND m.site_key = sl.site_key AND m.tenant_id = sl.tenant_id
GROUP BY 1,2,3,5
```

#### `dbt/models/marts/aggs/agg_stock_reconciliation.sql`
```sql
-- Grain: one row per (tenant_id, product_key, site_key, count_date)
-- Compares physical count vs calculated stock level
SELECT
    c.tenant_id, c.product_key, c.site_key, c.count_date,
    c.counted_quantity,
    sl.current_quantity AS calculated_quantity,
    c.counted_quantity - sl.current_quantity AS variance,
    ROUND((c.counted_quantity - sl.current_quantity) / NULLIF(sl.current_quantity, 0), 4) AS variance_pct
FROM {{ ref('fct_inventory_counts') }} c
INNER JOIN {{ ref('agg_stock_levels') }} sl ON c.product_key = sl.product_key AND c.site_key = sl.site_key AND c.tenant_id = sl.tenant_id
```

Create schema YAML: `dbt/models/marts/aggs/_aggs__inventory_schema.yml` and `dbt/models/marts/facts/_facts__inventory_schema.yml`.

---

### 5. Create Inventory Python Module

Follow the Route->Service->Repository pattern exactly. Read `src/datapulse/analytics/` for reference.

#### `src/datapulse/inventory/__init__.py`
Empty.

#### `src/datapulse/inventory/models.py`
```python
from __future__ import annotations
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from datapulse.types import JsonDecimal

class StockLevel(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_key: int
    drug_code: str
    drug_name: str
    drug_brand: str
    site_key: int
    site_code: str
    site_name: str
    current_quantity: JsonDecimal
    total_received: JsonDecimal
    total_dispensed: JsonDecimal
    total_wastage: JsonDecimal
    last_movement_date: date | None = None

class StockMovement(BaseModel):
    model_config = ConfigDict(frozen=True)
    movement_key: int
    movement_date: date
    movement_type: str
    drug_code: str
    drug_name: str
    site_code: str
    batch_number: str | None = None
    quantity: JsonDecimal
    unit_cost: JsonDecimal | None = None
    reference: str | None = None

class StockValuation(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_key: int
    drug_name: str
    current_quantity: JsonDecimal
    weighted_avg_cost: JsonDecimal
    stock_value: JsonDecimal

class InventoryFilter(BaseModel):
    model_config = ConfigDict(frozen=True)
    site_key: int | None = None
    drug_code: str | None = None
    movement_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int = Field(default=50, ge=1, le=500)

class AdjustmentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    drug_code: str
    site_code: str
    adjustment_type: str
    quantity: JsonDecimal
    batch_number: str | None = None
    reason: str
```

#### `src/datapulse/inventory/repository.py`
- `InventoryRepository(session: Session)`
- Methods: `get_stock_levels(filters)`, `get_stock_level_by_drug(drug_code, filters)`, `get_movements(filters)`, `get_movements_by_drug(drug_code, filters)`, `get_valuation(filters)`, `get_reorder_alerts(filters)`, `create_adjustment(tenant_id, request)`
- Use `text()` with parameterized queries. Use `build_where()` from `analytics/filters.py` where possible.

#### `src/datapulse/inventory/service.py`
- `InventoryService(repo: InventoryRepository, notification_svc: NotificationService | None = None)`
- Caching via `cache_get/set` pattern from analytics service
- Methods: `get_stock_levels(filters)`, `get_stock_level_detail(drug_code, filters)`, etc.
- On `create_adjustment`: if stock drops below reorder_point, create notification

---

### 6. Create API Routes

#### `src/datapulse/api/routes/inventory.py`
```python
from fastapi import APIRouter, Depends, Request, Response
from typing import Annotated

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(get_current_user)])

ServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]

@router.get("/stock-levels", response_model=list[StockLevel])
@limiter.limit("100/minute")
def get_stock_levels(
    request: Request, response: Response,
    service: ServiceDep,
    params: Annotated[InventoryQueryParams, Depends()],
    limits: Annotated[PlanLimits, Depends(get_tenant_plan_limits)],
    _: Annotated[None, Depends(require_permission("inventory:read"))],
) -> list[StockLevel]:
    if not limits.inventory_management:
        raise HTTPException(403, "Inventory management requires Pro plan or above")
    set_cache_headers(response, 300)
    return service.get_stock_levels(_to_filter(params))
```

10 endpoints total (see blueprint for full list).

### 7. Wire Dependencies

**Modify `src/datapulse/api/deps.py`**:
```python
def get_inventory_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> InventoryService:
    repo = InventoryRepository(session)
    return InventoryService(repo)
```

**Modify `src/datapulse/api/app.py`**:
```python
from datapulse.api.routes import inventory as inventory_routes

# In create_app():
if settings.feature_platform:
    app.include_router(inventory_routes.router, prefix="/api/v1")
```

---

### 8. Write Tests

- `tests/test_inventory_models.py` — Pydantic model validation, frozen check
- `tests/test_inventory_repository.py` — Mock session, test query generation
- `tests/test_inventory_service.py` — Mock repo, test caching + business logic
- `tests/test_inventory_endpoints.py` — TestClient with dependency overrides, test all 10 endpoints
- `tests/test_receipts_loader.py` — Mock Excel data, test column mapping + validation
- `tests/test_adjustments_loader.py` — Same pattern

Follow existing test patterns from `tests/conftest.py`.

---

## Verification Commands

```bash
# Loaders
pytest tests/test_receipts_loader.py tests/test_adjustments_loader.py -v

# dbt compile
cd dbt && dbt compile --select stg_stock_receipts stg_stock_adjustments stg_inventory_counts fct_stock_movements fct_inventory_counts agg_stock_levels agg_stock_valuation agg_stock_reconciliation

# Inventory module
pytest tests/test_inventory_*.py -v

# Full regression
pytest tests/ -x --timeout=120

# Lint
ruff format --check src/ tests/
ruff check src/ tests/
```

## Exit Criteria

- [ ] 3 loaders pass with mock Excel data
- [ ] 3 staging models + 2 fact models + 3 agg models compile in dbt
- [ ] `fct_stock_movements` correctly UNIONs 4 movement types
- [ ] `agg_stock_levels` computes correct running totals
- [ ] All 10 inventory endpoints return 200 with mocked repo data
- [ ] Plan gating returns 403 for starter plan
- [ ] RBAC permission check works (`inventory:read` required)
- [ ] All models are frozen Pydantic
- [ ] 95%+ coverage on new code
- [ ] All existing tests pass (zero regressions)
