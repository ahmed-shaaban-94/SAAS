# Silver Layer Audit Report

**Date**: 2026-04-07
**Auditor**: Claude (automated)
**Scope**: dbt staging models, macros used by silver, Python quality/pipeline scripts

---

## Files in Scope

| # | File | Role |
|---|------|------|
| 1 | `dbt/models/staging/stg_sales.sql` | Primary silver model (cleaned, deduped sales) |
| 2 | `dbt/models/staging/_staging__sources.yml` | Schema + tests for stg_sales |
| 3 | `dbt/models/bronze/bronze_sales.sql` | Bronze view consumed by stg_sales via `ref()` |
| 4 | `dbt/models/bronze/_bronze__sources.yml` | Source definition for bronze.sales |
| 5 | `dbt/macros/governorate_map.sql` | Governorate mapping macro (used by dim_site, not stg_sales directly) |
| 6 | `dbt/dbt_project.yml` | Project config (staging materialization) |
| 7 | `src/datapulse/pipeline/quality.py` | Silver quality checks (dedup, null rate, financial signs) |
| 8 | `src/datapulse/pipeline/quality_engine.py` | Configurable quality check engine with silver rules |
| 9 | `src/datapulse/pipeline/profiler.py` | Data profiler for silver table |
| 10 | `src/datapulse/pipeline/state_machine.py` | Pipeline state machine (SILVER + QUALITY_SILVER stages) |
| 11 | `src/datapulse/pipeline/rollback.py` | Rollback utilities (silver = idempotent, no rollback) |
| 12 | `src/datapulse/scheduler.py` | Pipeline orchestrator (Bronze -> Silver -> Gold) |

---

## Findings

### CRITICAL

---

#### C1. Dedup ROW_NUMBER lacks stable tiebreaker for non-unique `id` values

**File**: `dbt/models/staging/stg_sales.sql:80-83`
```sql
ROW_NUMBER() OVER (
    PARTITION BY tenant_id, reference_no, date, material, customer, site, quantity
    ORDER BY id
) AS row_num
```

**Why**: The dedup partition key includes `quantity` but NOT financial columns (`gross_sales`, `subtotal5_discount`). If two rows have the same `(tenant_id, reference_no, date, material, customer, site, quantity)` but different `gross_sales` values, the winner is determined solely by `ORDER BY id`. This is deterministic only if `id` is a monotonically assigned serial. If rows are ever re-loaded or `id` is reset between loads, the surviving row could flip between runs, causing non-reproducible results.

Additionally, `quantity` in the partition key is suspicious: two legitimate line items on the same invoice for the same product at the same site could have different quantities and would not be considered duplicates. Conversely, two genuine duplicates with a minor quantity difference (e.g., data entry correction) would both survive.

**Fix**: Add `gross_sales` to the partition key to distinguish rows that differ financially. Add `loaded_at DESC` as a secondary ORDER BY for a more stable tiebreaker that prefers the most recent load:
```sql
PARTITION BY tenant_id, reference_no, date, material, customer, site, quantity, gross_sales
ORDER BY loaded_at DESC, id DESC
```

**Test**: Add a dbt test that asserts the grain is unique after dedup:
```yaml
- name: stg_sales
  tests:
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns:
          - tenant_id
          - invoice_id
          - invoice_date
          - drug_code
          - customer_id
          - site_code
          - quantity
```

---

#### C2. Quality check references `reference_no` column which does not exist in silver table

**File**: `src/datapulse/pipeline/quality.py:32`
```python
_SILVER_CRITICAL_COLUMNS = ("reference_no", "date", "sales", "quantity")
```

**File**: `src/datapulse/pipeline/quality_engine.py:53`
```python
"columns": ["reference_no", "date", "sales", "quantity"],
```

**Why**: The silver model renames `reference_no` to `invoice_id` (line 95 of `stg_sales.sql`), and `date` to `invoice_date` (line 96). The quality null-rate check queries `public_staging.stg_sales` using the old bronze column names. This will cause a `column "reference_no" does not exist` SQL error at runtime, silently failing the quality gate or crashing the pipeline.

**Fix**: Update the silver critical columns to use the renamed column names:
```python
# quality.py
_SILVER_CRITICAL_COLUMNS = ("invoice_id", "invoice_date", "sales", "quantity")

# quality_engine.py silver default rule
"columns": ["invoice_id", "invoice_date", "sales", "quantity"],
```

Also update `_COLUMN_ALLOWLIST` in `quality.py` and `_ALLOWED_COLUMNS` in `quality_engine.py` to include `invoice_id` and `invoice_date`.

**Test**: Run `SELECT invoice_id, invoice_date, sales, quantity FROM public_staging.stg_sales LIMIT 1` to confirm the column names exist. Add a unit test that exercises `check_null_rate(session, run_id, stage="silver")`.

---

#### C3. NULL join keys cause silent row loss in downstream fact table

**File**: `dbt/models/staging/stg_sales.sql:95,113,137,144,149`
```sql
NULLIF(TRIM(reference_no), '')      AS invoice_id,    -- line 95
NULLIF(TRIM(material), '')          AS drug_code,      -- line 113
NULLIF(TRIM(customer), '')          AS customer_id,    -- line 137
NULLIF(TRIM(site), '')              AS site_code,      -- line 144
NULLIF(TRIM(personel_number), '')   AS staff_id,       -- line 149
```

**Why**: `NULLIF` converts empty strings to NULL. Downstream dimensions (`dim_product`, `dim_customer`, `dim_site`, `dim_staff`) filter `WHERE drug_code IS NOT NULL` etc. The fact table joins on these keys with `LEFT JOIN`, so NULL keys get `COALESCE(key, -1)` = -1 (Unknown). This is the intended design per the `assert_unknown_dimension_below_threshold` test, so the rows are not lost.

However, `invoice_id` is NULL-able (no `not_null` test by design per the YAML comment), yet it is used in `fct_sales.sales_key` surrogate hash:
```sql
COALESCE(s.invoice_id, '') || '|' || ...
```
Multiple rows with `invoice_id = NULL` for the same date/product/customer/site/quantity/billing will hash to the same `sales_key`, causing **hash collisions** and potential data loss when `fct_sales` is materialized as a table (duplicate keys silently overwrite if a uniqueness constraint is ever added).

**Fix**: Include a row-level identifier in the `fct_sales` surrogate key to prevent collisions. Alternatively, add a monotonically increasing sequence or use `source_file || loaded_at` as an additional tiebreaker in the hash.

**Test**: Add a dbt test to `fct_sales`:
```yaml
- name: sales_key
  tests:
    - unique
```

---

#### C4. `net_amount` description says "sales - discount" but formula does "sales + discount"

**File**: `dbt/models/staging/_staging__sources.yml:111`
```yaml
- name: net_amount
  description: "Net amount (sales - discount)"
```

**File**: `dbt/models/staging/stg_sales.sql:159`
```sql
ROUND((COALESCE(gross_sales, 0) + COALESCE(subtotal5_discount, 0))::NUMERIC, 2) AS net_amount
```

**Why**: The code comment on line 22 clarifies that `subtotal5_discount` is **NEGATIVE** in the ERP (e.g., -13.2 = EGP 13.2 discount). So the formula `gross_sales + subtotal5_discount` is mathematically correct (adding a negative = subtracting). However, the YAML description says "sales - discount" which is misleading — it implies the discount is positive and subtracted. A future developer might "fix" the formula to actually subtract, double-counting the discount.

**Fix**: Update the YAML description to match the actual formula:
```yaml
description: "Net amount (gross_sales + subtotal5_discount; discount is stored as negative)"
```

**Test**: Add a dbt test asserting `net_amount = sales + discount` for all rows.

---

### WARNINGS

---

#### W1. `COALESCE(quantity, 0)` and `COALESCE(gross_sales, 0)` mask NULL financials

**File**: `dbt/models/staging/stg_sales.sql:156-158`
```sql
COALESCE(quantity, 0)               AS quantity,
COALESCE(gross_sales, 0)            AS sales,
COALESCE(subtotal5_discount, 0)     AS discount,
```

**Why**: Replacing NULL with 0 makes it impossible to distinguish "no data" from "zero sales". A row with `gross_sales = NULL` (data quality issue) looks identical to a genuine zero-value transaction. This can inflate row counts in SUM aggregations where you expect to filter out bad data. The quality engine checks null rates on the bronze columns, but once coalesced to 0 in silver, the trail is lost.

**Fix**: Consider adding a `has_financial_data` boolean flag:
```sql
(gross_sales IS NOT NULL)  AS has_financial_data,
```
This preserves the COALESCE-to-0 convenience for dashboards while allowing analysts to filter out genuinely missing data.

**Test**: Monitor the percentage of rows where `sales = 0 AND quantity = 0` — a spike indicates a data load issue.

---

#### W2. `is_return` flag uses two independent detection methods that can conflict

**File**: `dbt/models/staging/stg_sales.sql:167-173`
```sql
CASE
    WHEN billing_type IN ('مرتجع توصيل', 'مرتجع اجل', 'مرتجع فورى',
                          'Pick-Up Order Return', 'مرتجع توصيل - اجل')
    THEN TRUE
    WHEN COALESCE(quantity, 0) < 0 THEN TRUE
    ELSE FALSE
END AS is_return,
```

**Why**: A row can have a positive quantity but a return billing type (e.g., an adjustment or correction), or negative quantity with a non-return billing type (e.g., a manual quantity correction). The dual-signal approach is pragmatic, but there's no alerting when these signals conflict. This could mask data quality issues.

**Fix**: Add a `return_signal_conflict` flag or a quality check:
```sql
(billing_type IN (...return types...) AND COALESCE(quantity, 0) >= 0) AS return_signal_conflict
```

**Test**: Add a quality check counting rows where the two signals disagree. If >1%, investigate.

---

#### W3. `is_walk_in` comparison uses raw bronze columns, not trimmed

**File**: `dbt/models/staging/stg_sales.sql:175`
```sql
(NULLIF(TRIM(customer), '') = NULLIF(TRIM(site), ''))    AS is_walk_in,
```

**Why**: This is actually correctly trimmed. However, the comparison is case-sensitive. If `customer = "ABC123"` and `site = "abc123"`, they won't match. Verify that customer and site codes use consistent casing in the source data. If not, this flag will under-count walk-ins.

**Fix**: Use case-insensitive comparison if codes can vary in case:
```sql
(UPPER(NULLIF(TRIM(customer), '')) = UPPER(NULLIF(TRIM(site), ''))) AS is_walk_in,
```

**Test**: Check for near-misses: `SELECT DISTINCT customer, site FROM stg_sales WHERE UPPER(customer) = UPPER(site) AND customer != site`.

---

#### W4. `drug_status` regex strips ALL whitespace before matching, losing multi-word statuses

**File**: `dbt/models/staging/stg_sales.sql:121-127`
```sql
WHEN UPPER(REGEXP_REPLACE(REGEXP_REPLACE(item_status, '[\s\u00A0]+', '', 'g'), '[-_]?T$', ''))
    IN ('ACTIVE') THEN 'Active'
```

**Why**: The inner `REGEXP_REPLACE` strips ALL whitespace characters from `item_status`. This means a multi-word status like "Not Active" would become "NOTACTIVE" and fall through to 'Unknown'. Currently the known statuses (Active, Cancelled, Canceled, Delisted, New) are all single words, so this works. But if the source adds a status like "Phase Out", it would silently map to 'Unknown'.

**Fix**: Replace whitespace-stripping with trimming only leading/trailing whitespace:
```sql
UPPER(TRIM(REGEXP_REPLACE(item_status, '[\u00A0]+', ' ', 'g')))
```

**Test**: Profile `item_status` values in bronze to confirm no multi-word statuses exist: `SELECT DISTINCT item_status FROM bronze.sales WHERE item_status ~ '\s'`.

---

#### W5. `billing_way` CASE WHEN has no ELSE clause for new Arabic billing types

**File**: `dbt/models/staging/stg_sales.sql:97-109`
```sql
CASE billing_type
    WHEN 'اجل' THEN 'Credit'
    ...
    ELSE TRIM(billing_type)
END AS billing_way,
```

**Why**: The ELSE passes through the raw `billing_type` untranslated. The `_staging__sources.yml` has an `accepted_values` test on `billing_way` that will **fail** if a new Arabic billing type appears in the source. This is actually a good thing (fail-fast), but the failure message will show the raw Arabic string, which may confuse operators.

**Fix**: Change ELSE to a sentinel value and log it:
```sql
ELSE 'Other (' || TRIM(billing_type) || ')'
```
Then add 'Other%' pattern handling in accepted_values, or keep the current approach and add documentation that new billing types require an update to this CASE.

**Test**: The existing `accepted_values` test on `billing_way` covers this. No additional test needed, but add an alert when it fails.

---

#### W6. `customer_name` cleanup regex misses edge cases

**File**: `dbt/models/staging/stg_sales.sql:139-143`
```sql
WHEN customer_name ~ '^[#\s\*\.]+$' THEN 'Unknown'
WHEN customer_name ~ '#' THEN REGEXP_REPLACE(customer_name, '[#]+', '', 'g')
ELSE TRIM(customer_name)
```

**Why**: The second branch removes `#` characters but does NOT trim the result. If `customer_name = "# Pharmacy"`, the result is `" Pharmacy"` with a leading space. Also, if after removing `#` characters the name becomes empty or all-spaces (e.g., `"###"`), the first regex would catch `"###"` but not `"## "` (has a trailing space after `#` chars).

**Fix**: Wrap the REGEXP_REPLACE in TRIM, and add a NULLIF for the empty-after-cleanup case:
```sql
WHEN customer_name ~ '#' THEN COALESCE(NULLIF(TRIM(REGEXP_REPLACE(customer_name, '[#]+', '', 'g')), ''), 'Unknown')
```

**Test**: `SELECT DISTINCT customer_name FROM stg_sales WHERE customer_name ~ '^\s' OR customer_name ~ '\s$'`.

---

### SUGGESTIONS

---

#### S1. Missing `unique` test on dedup grain columns in stg_sales

**File**: `dbt/models/staging/_staging__sources.yml`

**Why**: The schema YAML has tests for `not_null` and `accepted_values` but no uniqueness or relationship tests. After dedup (`WHERE row_num = 1`), the combination of `(tenant_id, invoice_id, invoice_date, drug_code, customer_id, site_code, quantity)` should be unique. Without a test, grain violations will silently propagate to the fact table.

**Fix**: Add a `dbt_utils.unique_combination_of_columns` test (requires `dbt-utils` package):
```yaml
tests:
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns:
        - tenant_id
        - invoice_id
        - invoice_date
        - drug_code
        - customer_id
        - site_code
        - quantity
```

---

#### S2. Missing `relationship` tests between stg_sales and dimensions

**File**: `dbt/models/staging/_staging__sources.yml`

**Why**: No relationship tests verify that `drug_code`, `customer_id`, `site_code`, `staff_id`, or `billing_way` in `stg_sales` have matching entries in their respective dimension tables. The `assert_unknown_dimension_below_threshold` test in marts catches this at >5%, but a relationship test would catch it at the individual-value level and report exactly which keys are unmatched.

**Fix**: Add relationship tests:
```yaml
- name: billing_way
  tests:
    - relationships:
        to: ref('dim_billing')
        field: billing_way
```

---

#### S3. No `not_null` test on `tenant_id`

**File**: `dbt/models/staging/_staging__sources.yml`

**Why**: `tenant_id` is used in RLS policies, dedup partitioning, and every dimension join. A NULL `tenant_id` would bypass RLS (the policy uses `= NULLIF(current_setting(...))::INT` which won't match NULL) and corrupt dedup logic. Yet there is no `not_null` test on this column.

**Fix**:
```yaml
- name: tenant_id
  description: "Tenant identifier for multi-tenancy"
  tests:
    - not_null
```

---

#### S4. No freshness test on silver table

**File**: `dbt/models/staging/_staging__sources.yml`

**Why**: The bronze source has a `loaded_at_field` freshness check (warn at 48h, error at 96h), but there is no equivalent for the silver layer. If dbt fails to run staging models, the silver table could go stale without any alert.

**Fix**: Add a quality engine rule for silver freshness, or add a `loaded_at` freshness check. The `quality_engine.py` already has a `freshness` check but it's only in the bronze default rules. Add it to silver defaults too:
```python
"silver": [
    ...existing rules...,
    {
        "check_name": "freshness",
        "severity": "warn",
        "config": {"max_age_hours": 48, "date_column": "invoice_date"},
    },
],
```

Note: `date_column` must also be updated to `invoice_date` for the silver table, and `invoice_date` must be added to `_ALLOWED_COLUMNS`.

---

#### S5. `SELECT *` usage in deduplicated CTE

**File**: `dbt/models/staging/stg_sales.sql:78-79`
```sql
deduplicated AS (
    SELECT
        *,
```

**Why**: Using `SELECT *` in the `deduplicated` CTE means any new column added to the bronze source will automatically flow through. While the final SELECT is explicit (no `SELECT *`), the `*` in the CTE is technically unnecessary since only explicitly named columns from `source` CTE are present. Low-risk since the `source` CTE already specifies exact columns.

**Fix**: Replace `*` with explicit column list from the `source` CTE. This is a minor code hygiene suggestion — the risk is minimal since `source` already enumerates columns.

---

#### S6. Repeated `COALESCE(NULLIF(TRIM(...), ''), 'default')` pattern should be a macro

**File**: `dbt/models/staging/stg_sales.sql` (lines 114-116, 131-134, 145-146, 150-152)

**Why**: The pattern `COALESCE(NULLIF(TRIM(col), ''), 'Fallback')` is repeated 12 times in the model. This is a classic candidate for a dbt macro to improve readability and ensure consistency.

**Fix**: Create a macro:
```sql
{% macro clean_text(column, default_value='Unknown') %}
    COALESCE(NULLIF(TRIM({{ column }}), ''), {{ "'" ~ default_value ~ "'" }})
{% endmacro %}
```
Then use: `{{ clean_text('material_desc') }} AS drug_name`

---

---

## Summary Table

| ID | Severity | File | Line(s) | Issue |
|----|----------|------|---------|-------|
| C1 | CRITICAL | `stg_sales.sql` | 80-83 | Dedup partition key may not be stable; missing `gross_sales` in key |
| C2 | CRITICAL | `quality.py`, `quality_engine.py` | 32, 53 | Silver null-rate check uses bronze column names (`reference_no`, `date`) instead of silver names (`invoice_id`, `invoice_date`) |
| C3 | CRITICAL | `stg_sales.sql` + `fct_sales.sql` | 95, 56-65 | NULL `invoice_id` causes hash collisions in `fct_sales.sales_key` |
| C4 | CRITICAL | `_staging__sources.yml` + `stg_sales.sql` | 111, 159 | `net_amount` description contradicts formula (discount is negative) |
| W1 | WARNING | `stg_sales.sql` | 156-158 | COALESCE(financial, 0) masks genuinely NULL data |
| W2 | WARNING | `stg_sales.sql` | 167-173 | `is_return` dual-signal can conflict with no alerting |
| W3 | WARNING | `stg_sales.sql` | 175 | `is_walk_in` case-sensitive comparison |
| W4 | WARNING | `stg_sales.sql` | 121-127 | Regex strips all whitespace, would break multi-word statuses |
| W5 | WARNING | `stg_sales.sql` | 97-109 | ELSE passthrough of untranslated billing types |
| W6 | WARNING | `stg_sales.sql` | 139-143 | `#` cleanup doesn't trim result, can leave leading spaces |
| S1 | SUGGESTION | `_staging__sources.yml` | - | Missing unique combination test on dedup grain |
| S2 | SUGGESTION | `_staging__sources.yml` | - | Missing relationship tests to dimensions |
| S3 | SUGGESTION | `_staging__sources.yml` | - | Missing `not_null` test on `tenant_id` |
| S4 | SUGGESTION | `quality_engine.py` | 47-61 | No freshness check for silver layer |
| S5 | SUGGESTION | `stg_sales.sql` | 78-79 | `SELECT *` in deduplicated CTE |
| S6 | SUGGESTION | `stg_sales.sql` | multiple | Repeated COALESCE/NULLIF/TRIM pattern should be a macro |

---

## Top 3 Fixes for Silver

### 1. Fix silver quality check column names (C2)
**Impact**: Pipeline crash or silent quality gate bypass
**Effort**: 15 minutes
**Files**: `quality.py:32`, `quality_engine.py:53`

The silver null-rate check will fail with a SQL error because it queries `reference_no` and `date` on a table where those columns have been renamed to `invoice_id` and `invoice_date`. This is a runtime bug that either crashes the quality gate or—if caught by a broad exception handler—allows bad data to pass unchecked.

### 2. Add unique grain test to stg_sales (S1 + C1)
**Impact**: Silent double-counting in all downstream aggregations
**Effort**: 30 minutes
**Files**: `_staging__sources.yml`, optionally `stg_sales.sql:80-83`

Without a uniqueness test on the dedup grain, there is no automated way to detect when two rows survive dedup that should have been collapsed. Adding a `dbt_utils.unique_combination_of_columns` test is the single highest-value test that can be added to the silver layer. Consider also adding `gross_sales` to the dedup partition key to prevent two rows with different financials from being treated as duplicates.

### 3. Add `not_null` test on `tenant_id` (S3)
**Impact**: RLS bypass + corrupted dedup logic
**Effort**: 5 minutes
**Files**: `_staging__sources.yml`

A NULL `tenant_id` would bypass the RLS policy (`tenant_id = NULLIF(...)::INT` never matches NULL), expose data cross-tenant, and corrupt the dedup partition. This is a one-line YAML addition with outsized security impact.
