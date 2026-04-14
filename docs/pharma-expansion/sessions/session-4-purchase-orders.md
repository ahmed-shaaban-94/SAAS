# Session 4: Purchase Orders & Suppliers — PO Workflow, Margins

## Context Brief

**DataPulse** is a pharma SaaS with medallion architecture. Python 3.11 / FastAPI / PostgreSQL 16 / dbt-core.

**What already exists**:
- Session 1: `bronze.suppliers`, `bronze.purchase_orders`, `bronze.po_lines` tables (migrations 053-055) with RLS. Bronze views + source definitions exist. `BronzeLoader` ABC in `src/datapulse/bronze/base_loader.py`. RBAC permissions: `purchase_orders:read/write`, `suppliers:read/write`.
- Session 2: `fct_stock_movements` (UNION of receipts + adjustments + dispenses + returns), `agg_stock_levels`, `src/datapulse/inventory/` module. **PO receipts should create entries in `bronze.stock_receipts`** which flow into `fct_stock_movements`.
- Existing dims: `dim_product` (17.8k drugs, drug_code + tenant_id), `dim_site` (2 sites, site_code + tenant_id), `dim_date`
- Existing: `fct_sales` with `sales` (gross_sales) and `quantity` columns per invoice line
- Billing `PlanLimits` has `purchase_orders: bool` field

**Goal**: Build supplier dimension, PO fact tables, PO receipt workflow (feeds into inventory), margin analysis (COGS vs revenue), and full Purchase Orders + Suppliers APIs (~12 endpoints).

---

## Task List

### 1. Create Column Maps and Loaders

#### `src/datapulse/bronze/suppliers_column_map.py`
```python
COLUMN_MAP: dict[str, str] = {
    "Supplier Code": "supplier_code",
    "Supplier Name": "supplier_name",
    "Contact Name": "contact_name",
    "Contact Phone": "contact_phone",
    "Contact Email": "contact_email",
    "Address": "address",
    "Payment Terms (Days)": "payment_terms_days",
    "Lead Time (Days)": "lead_time_days",
    "Active": "is_active",
    "Notes": "notes",
}
```

#### `src/datapulse/bronze/suppliers_loader.py`
`ExcelSuppliersLoader(BronzeLoader)` -> `bronze.suppliers`

#### `src/datapulse/bronze/po_column_map.py`
Two maps — one for PO headers, one for PO lines (same Excel, different sheets or sections):
```python
PO_HEADER_MAP: dict[str, str] = {
    "PO Number": "po_number",
    "PO Date": "po_date",
    "Supplier Code": "supplier_code",
    "Site Code": "site_code",
    "Status": "status",
    "Expected Date": "expected_date",
    "Notes": "notes",
}

PO_LINE_MAP: dict[str, str] = {
    "PO Number": "po_number",
    "Line Number": "line_number",
    "Drug Code": "drug_code",
    "Ordered Quantity": "ordered_quantity",
    "Unit Price": "unit_price",
    "Received Quantity": "received_quantity",
}
```

#### `src/datapulse/bronze/po_loader.py`
`ExcelPOLoader(BronzeLoader)` — handles both PO headers and lines from a single Excel file (2 sheets or 2 sections). Loads to `bronze.purchase_orders` + `bronze.po_lines`.

---

### 2. Create dbt Models

#### `dbt/models/staging/stg_suppliers.sql`
- Unique key: `['tenant_id', 'supplier_code']`
- SCD1 dedup via ROW_NUMBER
- Trim text, validate is_active boolean

#### `dbt/models/staging/stg_purchase_orders.sql`
- Unique key: `['tenant_id', 'po_number']`
- Dedup, validate status enum

#### `dbt/models/staging/stg_po_lines.sql`
- Unique key: `['tenant_id', 'po_number', 'line_number']`
- Validate quantities are non-negative

#### `dbt/models/marts/dims/dim_supplier.sql`
Follow `dim_product.sql` pattern:
```sql
-- Supplier dimension
-- SCD Type 1: latest attributes
-- supplier_key = MD5(tenant_id + supplier_code)
-- -1 Unknown row on full refresh

WITH ranked AS (
    SELECT
        tenant_id,
        supplier_code,
        supplier_name,
        contact_name, contact_phone, contact_email, address,
        payment_terms_days,
        lead_time_days,
        is_active,
        loaded_at,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, supplier_code
            ORDER BY loaded_at DESC
        ) AS rn
    FROM {{ ref('stg_suppliers') }}
)
SELECT
    ABS(('x' || LEFT(MD5(r.tenant_id::TEXT || '|' || r.supplier_code), 8))::BIT(32)::INT) AS supplier_key,
    r.*
FROM ranked r WHERE r.rn = 1
-- UNION ALL -1 Unknown row (on full refresh only)
```

#### `dbt/models/marts/facts/fct_purchase_orders.sql`
Header-level PO facts:
```sql
-- Grain: one row per purchase order
-- Joins to dim_supplier, dim_site
SELECT
    -- MD5 surrogate key
    po.tenant_id,
    COALESCE(sup.supplier_key, -1) AS supplier_key,
    COALESCE(s.site_key, -1) AS site_key,
    po.po_number,
    po.po_date,
    po.status,
    po.expected_date,
    -- Aggregate from lines
    SUM(pl.ordered_quantity * pl.unit_price) AS total_ordered_value,
    SUM(pl.received_quantity * pl.unit_price) AS total_received_value,
    COUNT(pl.line_number) AS line_count,
    -- Delivery performance
    CASE WHEN po.status = 'received'
        THEN (actual_receipt_date - po.po_date)
        ELSE NULL END AS actual_lead_days,
    po.loaded_at
FROM {{ ref('stg_purchase_orders') }} po
LEFT JOIN {{ ref('stg_po_lines') }} pl ON po.po_number = pl.po_number AND po.tenant_id = pl.tenant_id
LEFT JOIN {{ ref('dim_supplier') }} sup ON po.supplier_code = sup.supplier_code AND po.tenant_id = sup.tenant_id
LEFT JOIN {{ ref('dim_site') }} s ON po.site_code = s.site_code AND po.tenant_id = s.tenant_id
GROUP BY ...
```

#### `dbt/models/marts/facts/fct_po_lines.sql`
Line-level PO facts:
- Grain: one row per PO line item
- Joins to dim_product, dim_supplier
- Includes: ordered_qty, unit_price, received_qty, line_total, fulfillment_pct

#### `dbt/models/marts/aggs/agg_margin_analysis.sql`
COGS vs revenue per product:
```sql
-- Grain: one row per (tenant_id, product_key, year, month)
-- Computes: revenue (from fct_sales), COGS (from PO unit prices), margin
SELECT
    f.tenant_id,
    f.product_key,
    d.year, d.month,
    p.drug_name, p.drug_brand,
    SUM(f.sales) AS revenue,
    SUM(f.quantity * COALESCE(pol.weighted_unit_cost, 0)) AS cogs,
    SUM(f.sales) - SUM(f.quantity * COALESCE(pol.weighted_unit_cost, 0)) AS gross_margin,
    ROUND((SUM(f.sales) - SUM(f.quantity * COALESCE(pol.weighted_unit_cost, 0)))
        / NULLIF(SUM(f.sales), 0), 4) AS margin_pct
FROM {{ ref('fct_sales') }} f
INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
INNER JOIN {{ ref('dim_product') }} p ON f.product_key = p.product_key AND f.tenant_id = p.tenant_id
LEFT JOIN (
    -- Weighted average cost from PO lines
    SELECT tenant_id, drug_code,
        SUM(unit_price * received_quantity) / NULLIF(SUM(received_quantity), 0) AS weighted_unit_cost
    FROM {{ ref('fct_po_lines') }}
    GROUP BY 1, 2
) pol ON p.drug_code = pol.drug_code AND f.tenant_id = pol.tenant_id
GROUP BY 1,2,3,4,5,6
```

#### `dbt/models/marts/aggs/agg_supplier_performance.sql`
```sql
-- Grain: one row per (tenant_id, supplier_key)
-- Metrics: avg lead time, fill rate, order count, total spend
SELECT
    po.tenant_id,
    po.supplier_key,
    sup.supplier_name,
    COUNT(*) AS total_orders,
    AVG(po.actual_lead_days) AS avg_lead_days,
    SUM(po.total_received_value) / NULLIF(SUM(po.total_ordered_value), 0) AS fill_rate,
    SUM(po.total_ordered_value) AS total_spend,
    COUNT(CASE WHEN po.status = 'cancelled' THEN 1 END) AS cancelled_count
FROM {{ ref('fct_purchase_orders') }} po
INNER JOIN {{ ref('dim_supplier') }} sup ON po.supplier_key = sup.supplier_key AND po.tenant_id = sup.tenant_id
GROUP BY 1,2,3
```

---

### 3. Create Python Modules

#### `src/datapulse/purchase_orders/` — models.py, repository.py, service.py

**Models** (all frozen):
- `PurchaseOrder`: po_number, po_date, supplier_code, supplier_name, site_code, status, expected_date, total_ordered_value, total_received_value, line_count
- `POLine`: po_number, line_number, drug_code, drug_name, ordered_quantity, unit_price, received_quantity, line_total, fulfillment_pct
- `POCreateRequest`: po_date, supplier_code, site_code, expected_date, lines (list of {drug_code, quantity, unit_price})
- `POReceiveRequest`: po_number, lines (list of {line_number, received_quantity, batch_number, expiry_date})

**Service logic**:
- `create_po()`: Insert PO header + lines, set status='draft'
- `receive_po()`: Update received_qty on PO lines, create `bronze.stock_receipts` entries for each received line (feeds into inventory pipeline), update PO status (partial if not all lines filled, received if all)
- `cancel_po()`: Update status='cancelled' (only if draft/submitted)

#### `src/datapulse/suppliers/` — models.py, repository.py, service.py

**Models** (all frozen):
- `SupplierInfo`: supplier_code, supplier_name, contact_name, contact_phone, contact_email, address, payment_terms_days, lead_time_days, is_active
- `SupplierPerformance`: supplier_name, total_orders, avg_lead_days, fill_rate, total_spend
- `SupplierCreateRequest`: supplier_code, supplier_name, contact info fields
- `SupplierUpdateRequest`: partial update fields

---

### 4. Create API Routes

#### `src/datapulse/api/routes/purchase_orders.py` — 7 endpoints
- GET `/purchase-orders` — list with pagination + status filter
- POST `/purchase-orders` — create new PO
- GET `/purchase-orders/{po_number}` — PO detail with lines
- PUT `/purchase-orders/{po_number}` — update PO (draft only)
- POST `/purchase-orders/{po_number}/receive` — receive delivery (creates stock receipts)
- GET `/purchase-orders/{po_number}/lines` — PO lines
- GET `/margins/analysis` — margin analysis per product

#### `src/datapulse/api/routes/suppliers.py` — 5 endpoints
- GET `/suppliers` — list with is_active filter
- POST `/suppliers` — create supplier
- GET `/suppliers/{supplier_code}` — supplier detail
- PUT `/suppliers/{supplier_code}` — update supplier
- GET `/suppliers/{supplier_code}/performance` — performance metrics

All gated by `limits.purchase_orders` and `require_permission("purchase_orders:read/write")` or `"suppliers:read/write"`.

---

### 5. Wire Dependencies

- Add `get_po_service()` and `get_supplier_service()` to `deps.py`
- Register both routers in `app.py` (behind `feature_platform`)

---

### 6. Write Tests

- `tests/test_po_models.py`, `tests/test_po_repository.py`, `tests/test_po_service.py`
- `tests/test_po_endpoints.py` — all 7 PO endpoints + margin analysis
- `tests/test_suppliers_endpoints.py` — all 5 supplier endpoints
- `tests/test_po_loader.py`, `tests/test_suppliers_loader.py`
- Critical test: PO receive -> stock receipt creation -> fct_stock_movements flow

---

## Verification Commands

```bash
pytest tests/test_po_*.py tests/test_suppliers_*.py -v
cd dbt && dbt compile --select stg_suppliers stg_purchase_orders stg_po_lines dim_supplier fct_purchase_orders fct_po_lines agg_margin_analysis agg_supplier_performance
pytest tests/ -x --timeout=120
ruff format --check src/ tests/
ruff check src/ tests/
```

## Exit Criteria

- [ ] `dim_supplier` generates correct MD5 keys with -1 Unknown row
- [ ] PO create validates required fields (supplier_code, at least 1 line)
- [ ] PO receive creates stock_receipt entries that flow through to `fct_stock_movements`
- [ ] Partial delivery correctly updates received_quantity and PO status
- [ ] `agg_margin_analysis` computes COGS from PO unit prices and margin correctly
- [ ] `agg_supplier_performance` computes avg lead time and fill rate
- [ ] All endpoints gated by plan + permissions
- [ ] 95%+ coverage on new code
- [ ] All existing tests pass
