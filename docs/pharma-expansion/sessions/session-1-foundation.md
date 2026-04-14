# Session 1: Foundation — Billing Tier, Pluggable Loader, Migrations, Permissions

## Context Brief

**DataPulse** is a pharma sales analytics SaaS built on a medallion architecture:
- **Stack**: Python 3.11 / FastAPI / PostgreSQL 16 / dbt-core / Polars / Next.js 14
- **Data**: 2.27M sales rows in `bronze.sales`, transformed through `stg_sales` -> 6 dims + `fct_sales` -> 8 aggs + 11 features
- **Patterns**: Route->Service->Repository, RLS per tenant, Pydantic frozen models, structlog, 95%+ test coverage
- **Billing**: Stripe subscriptions with `PlanLimits` frozen dataclass in `src/datapulse/billing/plans.py`
- **RBAC**: Role-based access with `AccessContext` and `require_permission("domain:action")` in `src/datapulse/rbac/dependencies.py`
- **Current gap**: Only invoice-level sales data — no inventory, stock, expiry, purchase, or POS data

**Goal of this session**: Create the shared foundation that ALL subsequent sessions depend on — 10 database migrations, updated billing tiers, a pluggable loader interface, and RBAC permissions for 5 new domains.

**This is Session 1 of 8** in the Pharmaceutical Platform Expansion. No prior sessions exist.

---

## Task List

### 1. Create 10 Database Migrations (050-059)

All migrations go in `migrations/` directory. The latest existing migration is `049_create_ai_invocations.sql`.

**Pattern** (from migration 049):
```sql
-- Migration: NNN — description
-- Layer: Bronze | Application | Infrastructure
-- Idempotent.

CREATE TABLE IF NOT EXISTS schema.table_name (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id     INT NOT NULL DEFAULT 1,
    -- columns with NUMERIC(18,4) for financials
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_table_tenant ON schema.table_name(tenant_id);

ALTER TABLE schema.table_name ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema.table_name FORCE  ROW LEVEL SECURITY;

-- Use DO $$ for idempotent policy creation
DO $$ BEGIN
    CREATE POLICY owner_all ON schema.table_name
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON schema.table_name
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE schema.table_name TO datapulse_reader;

COMMENT ON TABLE schema.table_name IS 'Description. RLS-protected.';
```

#### Migration 050: `050_create_inventory_schema.sql`
Create 3 tables in `bronze` schema:

**`bronze.stock_receipts`**:
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `source_file TEXT NOT NULL`
- `loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `receipt_date DATE`
- `receipt_reference TEXT` — supplier delivery note / GRN number
- `drug_code TEXT` — joins to dim_product
- `site_code TEXT` — joins to dim_site
- `batch_number TEXT`
- `expiry_date DATE`
- `quantity NUMERIC(18,4)`
- `unit_cost NUMERIC(18,4)`
- `supplier_code TEXT`
- `po_reference TEXT`
- `notes TEXT`
- Indexes: `(tenant_id)`, `(tenant_id, drug_code, site_code)`, `(loaded_at DESC)`

**`bronze.stock_adjustments`**:
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `source_file TEXT NOT NULL`
- `loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `adjustment_date DATE`
- `adjustment_type TEXT CHECK (adjustment_type IN ('damage','shrinkage','transfer_in','transfer_out','correction','write_off'))`
- `drug_code TEXT`
- `site_code TEXT`
- `batch_number TEXT`
- `quantity NUMERIC(18,4)` — positive = add, negative = remove
- `reason TEXT`
- `authorized_by TEXT`
- `notes TEXT`
- Indexes: `(tenant_id)`, `(tenant_id, drug_code, site_code)`, `(loaded_at DESC)`

**`bronze.inventory_counts`**:
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `source_file TEXT NOT NULL`
- `loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `count_date DATE`
- `drug_code TEXT`
- `site_code TEXT`
- `batch_number TEXT`
- `counted_quantity NUMERIC(18,4)`
- `counted_by TEXT`
- `notes TEXT`
- Indexes: `(tenant_id)`, `(tenant_id, drug_code, site_code)`, `(loaded_at DESC)`

All 3 tables get: ENABLE RLS, FORCE RLS, owner_all + reader_select policies, GRANT SELECT.

#### Migration 051: `051_create_reorder_config.sql`
**`public.reorder_config`** — application table (CRUD via API):
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `drug_code TEXT NOT NULL`
- `site_code TEXT NOT NULL`
- `min_stock NUMERIC(18,4) NOT NULL DEFAULT 0`
- `reorder_point NUMERIC(18,4) NOT NULL DEFAULT 0`
- `max_stock NUMERIC(18,4) NOT NULL DEFAULT 0`
- `reorder_lead_days INT NOT NULL DEFAULT 7`
- `is_active BOOLEAN NOT NULL DEFAULT true`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_by TEXT`
- `UNIQUE(tenant_id, drug_code, site_code)`
- Indexes: `(tenant_id, drug_code, site_code, is_active)`
- RLS + grants

#### Migration 052: `052_create_batches.sql`
**`bronze.batches`** — batch/lot master with expiry:
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `source_file TEXT NOT NULL DEFAULT 'manual'`
- `loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `drug_code TEXT NOT NULL`
- `site_code TEXT NOT NULL`
- `batch_number TEXT NOT NULL`
- `expiry_date DATE NOT NULL`
- `initial_quantity NUMERIC(18,4) NOT NULL`
- `current_quantity NUMERIC(18,4) NOT NULL`
- `unit_cost NUMERIC(18,4)`
- `status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','near_expiry','expired','quarantined','written_off'))`
- `quarantine_date DATE`
- `write_off_date DATE`
- `write_off_reason TEXT`
- `UNIQUE(tenant_id, drug_code, site_code, batch_number)`
- Indexes: `(tenant_id, expiry_date)`, `(tenant_id, status)`, `(tenant_id, drug_code, site_code)`
- RLS + grants

#### Migration 053: `053_create_suppliers.sql`
**`bronze.suppliers`**:
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `source_file TEXT NOT NULL DEFAULT 'manual'`
- `loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `supplier_code TEXT NOT NULL`
- `supplier_name TEXT NOT NULL`
- `contact_name TEXT`, `contact_phone TEXT`, `contact_email TEXT`, `address TEXT`
- `payment_terms_days INT DEFAULT 30`
- `lead_time_days INT DEFAULT 7`
- `is_active BOOLEAN NOT NULL DEFAULT true`
- `notes TEXT`
- `UNIQUE(tenant_id, supplier_code)`
- Indexes: `(tenant_id, supplier_code)`, `(tenant_id, is_active)`
- RLS + grants

#### Migration 054: `054_create_purchase_orders.sql`
**`bronze.purchase_orders`**:
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `source_file TEXT NOT NULL DEFAULT 'manual'`
- `loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `po_number TEXT NOT NULL`
- `po_date DATE NOT NULL`
- `supplier_code TEXT NOT NULL`
- `site_code TEXT NOT NULL`
- `status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','partial','received','cancelled'))`
- `expected_date DATE`
- `total_amount NUMERIC(18,4)`
- `notes TEXT`
- `created_by TEXT`
- `UNIQUE(tenant_id, po_number)`
- Indexes: `(tenant_id, po_number)`, `(tenant_id, status)`, `(tenant_id, supplier_code)`, `(tenant_id, po_date DESC)`
- RLS + grants

#### Migration 055: `055_create_po_lines.sql`
**`bronze.po_lines`**:
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `po_number TEXT NOT NULL`
- `line_number INT NOT NULL`
- `drug_code TEXT NOT NULL`
- `ordered_quantity NUMERIC(18,4) NOT NULL`
- `unit_price NUMERIC(18,4) NOT NULL`
- `received_quantity NUMERIC(18,4) NOT NULL DEFAULT 0`
- `line_total NUMERIC(18,4) GENERATED ALWAYS AS (ordered_quantity * unit_price) STORED`
- `UNIQUE(tenant_id, po_number, line_number)`
- Indexes: `(tenant_id, po_number)`, `(tenant_id, drug_code)`
- RLS + grants

#### Migration 056: `056_create_pos_transactions.sql`
**`bronze.pos_transactions`** — design-only table (empty but ready):
- `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
- `tenant_id INT NOT NULL`
- `source_type TEXT NOT NULL DEFAULT 'pos_api' CHECK (source_type IN ('pos_api','manual','excel'))`
- `loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `transaction_id TEXT NOT NULL`
- `transaction_date TIMESTAMPTZ NOT NULL`
- `site_code TEXT NOT NULL`
- `register_id TEXT`
- `cashier_id TEXT`
- `customer_id TEXT`
- `drug_code TEXT NOT NULL`
- `batch_number TEXT`
- `quantity NUMERIC(18,4) NOT NULL`
- `unit_price NUMERIC(18,4) NOT NULL`
- `discount NUMERIC(18,4) DEFAULT 0`
- `net_amount NUMERIC(18,4) NOT NULL`
- `payment_method TEXT CHECK (payment_method IN ('cash','card','insurance','mixed'))`
- `insurance_no TEXT`
- `is_return BOOLEAN NOT NULL DEFAULT false`
- `pharmacist_id TEXT`
- `UNIQUE(tenant_id, transaction_id, drug_code)`
- Indexes: `(tenant_id, transaction_date DESC)`, `(tenant_id, drug_code)`, `(tenant_id, site_code)`
- RLS + grants

#### Migration 057: `057_grant_new_tables_to_reader.sql`
```sql
GRANT SELECT ON TABLE bronze.stock_receipts TO datapulse_reader;
GRANT SELECT ON TABLE bronze.stock_adjustments TO datapulse_reader;
GRANT SELECT ON TABLE bronze.inventory_counts TO datapulse_reader;
GRANT SELECT ON TABLE public.reorder_config TO datapulse_reader;
GRANT SELECT ON TABLE bronze.batches TO datapulse_reader;
GRANT SELECT ON TABLE bronze.suppliers TO datapulse_reader;
GRANT SELECT ON TABLE bronze.purchase_orders TO datapulse_reader;
GRANT SELECT ON TABLE bronze.po_lines TO datapulse_reader;
GRANT SELECT ON TABLE bronze.pos_transactions TO datapulse_reader;
```

#### Migration 058: `058_create_inventory_permissions.sql`
Insert new RBAC permission strings. Check how existing permissions are stored — look at `src/datapulse/rbac/` for the permissions table/model.

New permissions: `inventory:read`, `inventory:write`, `inventory:adjust`, `dispensing:read`, `expiry:read`, `expiry:write`, `purchase_orders:read`, `purchase_orders:write`, `suppliers:read`, `suppliers:write`

Add these to `editor` and `admin` role defaults.

#### Migration 059: `059_add_movement_tracking_indexes.sql`
Additional composite indexes for query performance:
- `(tenant_id, drug_code, site_code, receipt_date)` on stock_receipts
- `(tenant_id, drug_code, site_code, adjustment_date)` on stock_adjustments
- `(tenant_id, drug_code, site_code, count_date)` on inventory_counts

---

### 2. Update Billing Plans

**File**: `src/datapulse/billing/plans.py`

Current `PlanLimits` has 7 fields. Add 8 new fields with defaults:

```python
@dataclass(frozen=True)
class PlanLimits:
    # Existing fields (do not modify)
    data_sources: int
    max_rows: int
    ai_insights: bool
    pipeline_automation: bool
    quality_gates: bool
    name: str
    price_display: str

    # NEW platform tier fields
    inventory_management: bool = False
    expiry_tracking: bool = False
    dispensing_analytics: bool = False
    purchase_orders: bool = False
    pos_integration: bool = False
    max_stock_items: int = 0          # 0 = disabled, -1 = unlimited
    max_suppliers: int = 0
    stock_alerts: bool = False
```

Update tier assignments:
- `starter`: all False/0 (no platform features)
- `pro`: inventory_management=True, expiry_tracking=True, dispensing_analytics=True, purchase_orders=True, pos_integration=False, max_stock_items=50_000, max_suppliers=500, stock_alerts=True
- `enterprise`: all True, max_stock_items=-1, max_suppliers=-1

---

### 3. Create Pluggable Loader Interface

**File**: `src/datapulse/bronze/base_loader.py`

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import polars as pl
from sqlalchemy import Engine

@dataclass(frozen=True)
class LoadResult:
    """Immutable result from a loader run."""
    source_type: str        # 'excel' | 'pos_api' | 'manual'
    table_name: str         # e.g. 'bronze.stock_receipts'
    rows_loaded: int
    rows_skipped: int
    errors: tuple[str, ...]  # immutable

class BronzeLoader(ABC):
    """Abstract base for all bronze-layer data loaders.

    Template method pattern: discover -> read -> validate -> load.
    Follows existing bronze/loader.py patterns.
    """

    @abstractmethod
    def discover(self) -> list[Any]:
        """Discover data sources (files, API endpoints, etc.)."""
        ...

    @abstractmethod
    def read(self, source: Any) -> pl.DataFrame:
        """Read a single source into a Polars DataFrame."""
        ...

    @abstractmethod
    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Validate and clean the DataFrame. Raise on critical errors."""
        ...

    @abstractmethod
    def get_column_map(self) -> dict[str, str]:
        """Return the Excel header -> DB column name mapping."""
        ...

    @abstractmethod
    def get_allowed_columns(self) -> frozenset[str]:
        """Return the whitelist of allowed DB column names."""
        ...

    @abstractmethod
    def get_target_table(self) -> str:
        """Return the target table name (e.g. 'bronze.stock_receipts')."""
        ...

    def run(self, engine: Engine, batch_size: int = 50_000, tenant_id: int = 1) -> LoadResult:
        """Template method: discover -> read -> validate -> load.
        Follows exact pattern of existing loader.run().
        """
        # Implementation: iterate sources, read each, validate, batch insert
        # Use _validate_columns pattern from existing loader.py
        # Parameterized INSERT (no f-string SQL)
        ...
```

**File**: `src/datapulse/bronze/registry.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datapulse.bronze.base_loader import BronzeLoader

LOADER_REGISTRY: dict[str, type[BronzeLoader]] = {}
# Populated by each loader module on import, or manually:
# "stock_receipts": ExcelReceiptsLoader,
# "stock_adjustments": ExcelAdjustmentsLoader,
# etc.
```

---

### 4. Add Feature Flag to Config

**File**: `src/datapulse/config.py` (or `src/datapulse/core/config.py` — check which exists)

Add `feature_platform: bool = False` to the Settings class.

---

### 5. Create dbt Bronze Source Definitions

**File**: `dbt/models/bronze/_bronze__inventory_sources.yml`

Follow pattern from `dbt/models/bronze/_bronze__sources.yml`:
```yaml
version: 2

sources:
  - name: bronze
    schema: bronze
    description: "Bronze layer — raw data loaded from Excel files and manual entry"
    tables:
      - name: stock_receipts
        description: "Raw stock receipt records from Excel import or manual entry"
        loaded_at_field: loaded_at
        columns:
          - name: id
            description: "Auto-generated primary key"
          - name: tenant_id
            description: "Tenant identifier for RLS"
          - name: drug_code
            description: "Product code, joins to dim_product"
          # ... etc for each column

      - name: stock_adjustments
        description: "Manual stock adjustments (damage, shrinkage, transfers, corrections)"
        loaded_at_field: loaded_at

      - name: inventory_counts
        description: "Physical stock count records for reconciliation"
        loaded_at_field: loaded_at

      - name: batches
        description: "Batch/lot records with expiry dates"
        loaded_at_field: loaded_at

      - name: suppliers
        description: "Supplier directory"
        loaded_at_field: loaded_at

      - name: purchase_orders
        description: "Purchase order headers"
        loaded_at_field: loaded_at

      - name: po_lines
        description: "Purchase order line items"
        loaded_at_field: loaded_at

      - name: pos_transactions
        description: "POS transaction records (design-only, populated later)"
        loaded_at_field: loaded_at
```

### 6. Create 7 Bronze View Models

Follow the exact pattern from `dbt/models/bronze/bronze_sales.sql`:

```sql
{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze [table] view: direct reference to the raw bronze.[table] table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    tenant_id,
    source_file,
    loaded_at,
    -- ... all columns for the table
FROM {{ source('bronze', 'table_name') }}
```

Create one view for each: `bronze_stock_receipts.sql`, `bronze_stock_adjustments.sql`, `bronze_inventory_counts.sql`, `bronze_batches.sql`, `bronze_suppliers.sql`, `bronze_purchase_orders.sql`, `bronze_po_lines.sql`.

---

### 7. Write Tests

**`tests/test_billing_plans_platform.py`**:
- Test that PlanLimits has all new fields with correct defaults
- Test starter/pro/enterprise tier assignments
- Test `get_plan_limits()` returns correct tier
- Test unknown plan falls back to starter

**`tests/test_base_loader.py`**:
- Test that BronzeLoader is abstract (cannot instantiate)
- Test LoadResult is frozen
- Test a concrete subclass can be created and run

---

## Files Summary

| Action | Path |
|--------|------|
| CREATE | `migrations/050_create_inventory_schema.sql` |
| CREATE | `migrations/051_create_reorder_config.sql` |
| CREATE | `migrations/052_create_batches.sql` |
| CREATE | `migrations/053_create_suppliers.sql` |
| CREATE | `migrations/054_create_purchase_orders.sql` |
| CREATE | `migrations/055_create_po_lines.sql` |
| CREATE | `migrations/056_create_pos_transactions.sql` |
| CREATE | `migrations/057_grant_new_tables_to_reader.sql` |
| CREATE | `migrations/058_create_inventory_permissions.sql` |
| CREATE | `migrations/059_add_movement_tracking_indexes.sql` |
| MODIFY | `src/datapulse/billing/plans.py` |
| CREATE | `src/datapulse/bronze/base_loader.py` |
| CREATE | `src/datapulse/bronze/registry.py` |
| MODIFY | `src/datapulse/config.py` (or `core/config.py`) |
| CREATE | `dbt/models/bronze/_bronze__inventory_sources.yml` |
| CREATE | `dbt/models/bronze/bronze_stock_receipts.sql` |
| CREATE | `dbt/models/bronze/bronze_stock_adjustments.sql` |
| CREATE | `dbt/models/bronze/bronze_inventory_counts.sql` |
| CREATE | `dbt/models/bronze/bronze_batches.sql` |
| CREATE | `dbt/models/bronze/bronze_suppliers.sql` |
| CREATE | `dbt/models/bronze/bronze_purchase_orders.sql` |
| CREATE | `dbt/models/bronze/bronze_po_lines.sql` |
| CREATE | `tests/test_billing_plans_platform.py` |
| CREATE | `tests/test_base_loader.py` |

---

## Verification Commands

```bash
# 1. Run migrations against test DB
docker exec -it datapulse-db psql -U datapulse -d datapulse -c "\dt bronze.*"

# 2. Test billing plans
pytest tests/test_billing_plans_platform.py -v

# 3. Test loader interface
pytest tests/test_base_loader.py -v

# 4. dbt compile new sources
cd dbt && dbt compile --select source:bronze.*

# 5. dbt compile bronze views
cd dbt && dbt compile --select bronze_stock_receipts bronze_stock_adjustments bronze_inventory_counts bronze_batches bronze_suppliers bronze_purchase_orders bronze_po_lines

# 6. Full regression — zero regressions
pytest tests/ -x --timeout=120

# 7. Lint
ruff format --check src/ tests/
ruff check src/ tests/
```

---

## Exit Criteria

- [ ] All 10 migrations apply cleanly (idempotent — can run twice)
- [ ] All 9 new tables exist in PostgreSQL with RLS enabled and forced
- [ ] `PlanLimits` dataclass has 8 new fields with correct defaults
- [ ] `get_plan_limits("pro")` returns `inventory_management=True`
- [ ] `get_plan_limits("starter")` returns `inventory_management=False`
- [ ] `BronzeLoader` ABC exists and cannot be instantiated directly
- [ ] `LoadResult` is frozen (immutable)
- [ ] All 7 bronze dbt views compile successfully
- [ ] Source freshness check compiles for new sources
- [ ] All existing tests pass (zero regressions)
- [ ] New tests pass with 95%+ coverage on new code
- [ ] `ruff check` passes with no errors
