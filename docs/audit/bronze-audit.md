# Bronze Layer Audit Report

**Date**: 2026-04-07
**Scope**: Bronze layer — raw ingestion pipeline, dbt bronze model, source definitions, migrations
**Auditor**: Claude Code (read-only)

---

## Files in Scope

| # | File | Purpose |
|---|------|---------|
| 1 | `src/datapulse/bronze/loader.py` | Python Excel-to-Parquet-to-PostgreSQL pipeline |
| 2 | `src/datapulse/bronze/column_map.py` | Excel header -> DB column mapping |
| 3 | `src/datapulse/bronze/__init__.py` | Package init |
| 4 | `src/datapulse/bronze/__main__.py` | CLI entry point |
| 5 | `dbt/models/bronze/bronze_sales.sql` | dbt view model over bronze.sales |
| 6 | `dbt/models/bronze/_bronze__sources.yml` | Source definition + freshness |
| 7 | `dbt/models/staging/stg_sales.sql` | Silver model (refs bronze — checked for silent row drops) |
| 8 | `dbt/models/staging/_staging__sources.yml` | Staging column docs |
| 9 | `dbt/dbt_project.yml` | Project-level materialization config |
| 10 | `migrations/001_create_bronze_schema.sql` | DDL for bronze.sales table |
| 11 | `migrations/003_add_tenant_id.sql` | Adds tenant_id + RLS |
| 12 | `src/datapulse/pipeline/executor.py` | Pipeline executor (calls bronze loader) |
| 13 | `src/datapulse/pipeline/quality.py` | Quality gate checks for bronze stage |
| 14 | `src/datapulse/pipeline/rollback.py` | Rollback logic for bronze inserts |
| 15 | `src/datapulse/core/config.py` | Settings (bronze_batch_size, paths) |
| 16 | `dbt/seeds/seed_division_origin.csv` | Division-to-origin mapping seed |
| 17 | `dbt/seeds/seed_budget_2025.csv` | Budget seed (Arabic site names) |

---

## Findings

### RED-1: No Idempotency — Re-running Loader Duplicates All Rows

**Severity**: RED (Critical)
**File**: `src/datapulse/bronze/loader.py:176-185`

```python
insert_sql = text(f"INSERT INTO bronze.sales ({col_names}) VALUES ({placeholders})")

for offset in range(0, total_rows, batch_size):
    batch = df_to_load.slice(offset, batch_size)
    rows_dicts = batch.to_dicts()
    conn.execute(insert_sql, rows_dicts)
```

**Why wrong**: The loader performs bare `INSERT` without any deduplication strategy. Running the pipeline twice on the same Excel files doubles all rows in `bronze.sales`. There is no:
- `TRUNCATE` before load (full-refresh strategy)
- `DELETE WHERE source_quarter = :quarter` (partition replacement)
- `ON CONFLICT` / upsert logic
- `unique_key` constraint on business keys

The silver layer deduplicates via `ROW_NUMBER()`, so downstream is protected — but bronze grows unboundedly, wasting storage and slowing quality checks that query `bronze.sales` directly (e.g., `check_row_count`, `check_null_rate`).

**Fix**: Add a quarter-scoped delete-before-insert pattern:
```python
with engine.begin() as conn:
    conn.execute(
        text("DELETE FROM bronze.sales WHERE source_quarter = :q AND tenant_id = :t"),
        {"q": quarter, "t": tenant_id},
    )
    # ... then INSERT as before
```
Alternatively, truncate/reload or use a staging temp table with `INSERT ... ON CONFLICT`.

**Test to add**: dbt test `unique` on `(source_file, reference_no, date, material, customer, site, quantity)` in `_bronze__sources.yml` or a Python integration test that loads the same file twice and asserts row count doesn't double.

---

### RED-2: Rollback References Non-Existent Column `_pipeline_run_id`

**Severity**: RED (Critical)
**File**: `src/datapulse/pipeline/rollback.py:28`

```python
result = session.execute(
    text("DELETE FROM bronze.sales WHERE _pipeline_run_id = :run_id"),
    {"run_id": str(run_id)},
)
```

**Why wrong**: The `bronze.sales` table (defined in `migrations/001_create_bronze_schema.sql`) has **no** `_pipeline_run_id` column. The loader (`loader.py`) never inserts a pipeline run ID either — `ALLOWED_COLUMNS` is derived from `COLUMN_MAP.values() | {"source_file", "source_quarter"}`, which does not include `_pipeline_run_id`.

This means `rollback_bronze()` will always raise a `ProgrammingError` (column does not exist), which is caught by the `except` clause and returns 0. **Bronze rollback is silently broken.**

**Fix**: Either:
1. Add `_pipeline_run_id UUID` column to `bronze.sales` via a new migration, and pass `run_id` through `load_to_postgres()` into every INSERT.
2. Change rollback to use `loaded_at` range or `source_quarter` as the delete key (less precise but functional).

**Test to add**: Integration test that triggers `rollback_bronze()` against a real DB and asserts rows are actually deleted.

---

### RED-3: No Unique Constraint on Business Keys in `bronze.sales`

**Severity**: RED (Critical)
**File**: `migrations/001_create_bronze_schema.sql:6-76`

```sql
CREATE TABLE IF NOT EXISTS bronze.sales (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- ... 47 columns, all TEXT or NUMERIC, no UNIQUE constraint
);
```

**Why wrong**: The only uniqueness guarantee is on `id` (surrogate). There is no composite unique constraint or index on business keys like `(tenant_id, reference_no, date, material, customer, site, quantity)`. Combined with RED-1 (no idempotency), duplicate rows can accumulate silently. The dedup key used in `stg_sales.sql:80-82` (`PARTITION BY tenant_id, reference_no, date, material, customer, site, quantity`) implicitly defines what "unique" means, but this contract is not enforced at the bronze level.

**Fix**: Add a composite unique index (or unique constraint) matching the silver dedup key:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_bronze_sales_bk
    ON bronze.sales (tenant_id, reference_no, date, material, customer, site, quantity);
```
If exact duplicates from source are expected (same business key, same values), use `ON CONFLICT DO NOTHING` in the loader.

**Test to add**: dbt source test:
```yaml
- name: sales
  columns:
    - name: reference_no
      tests:
        - not_null  # or at least a custom test for composite uniqueness
```

---

### RED-4: `tenant_id` Not Passed by Python Loader

**Severity**: RED (Critical)
**File**: `src/datapulse/bronze/loader.py:26-29`

```python
ALLOWED_COLUMNS: frozenset[str] = frozenset(COLUMN_MAP.values()) | {
    "source_file",
    "source_quarter",
}
```

**Why wrong**: `tenant_id` is not in `ALLOWED_COLUMNS` and is never set by the loader. It relies entirely on the DB default (`DEFAULT 1` from migration 003). This works for single-tenant but:
1. When multi-tenancy ships (Phase 5), the loader has no mechanism to specify tenant.
2. If `DEFAULT 1` is ever removed, all inserts will fail with a NOT NULL violation.
3. The `_validate_columns()` function would reject `tenant_id` if someone tried to add it to the DataFrame.

**Fix**: Add `tenant_id` to `ALLOWED_COLUMNS` and inject it as a column in the DataFrame:
```python
ALLOWED_COLUMNS: frozenset[str] = frozenset(COLUMN_MAP.values()) | {
    "source_file",
    "source_quarter",
    "tenant_id",
}
```
And in `run()`, add `tenant_id` to the DataFrame before loading:
```python
chunk_df = chunk_df.with_columns(pl.lit(tenant_id).alias("tenant_id"))
```

**Test to add**: Unit test asserting `tenant_id` appears in the DataFrame columns before `load_to_postgres`.

---

### RED-5: Silent Row Drops — Dedup in Silver Uses `quantity` as Key Component

**Severity**: RED (Critical)
**File**: `dbt/models/staging/stg_sales.sql:78-83`

```sql
deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, reference_no, date, material, customer, site, quantity
            ORDER BY id
        ) AS row_num
    FROM source
)
...
WHERE row_num = 1
```

**Why wrong**: Including `quantity` in the dedup partition key means two rows with the same invoice/date/product/customer/site but **different quantities** are treated as distinct — they are not deduplicated. But two rows with the same invoice and same quantity ARE deduped, which could silently drop legitimate line items (e.g., two identical purchases on the same invoice).

This is a design risk: if the source Excel legitimately has two rows where a customer bought the same product, same quantity, on the same invoice, the second row is silently dropped. There is no audit trail of dropped rows.

**Fix**: Consider whether `quantity` should be in the partition key at all. If it must stay, add an `_dedup_dropped` count metric to quality checks so dropped rows are visible. Alternatively, add `id` (the bronze surrogate) to detect true duplicates (same `id` = re-ingested, different `id` = distinct line item).

**Test to add**: Quality check comparing `COUNT(*)` bronze vs silver, with an alert if dedup drops >X% of rows.

---

### RED-6: Excel Numeric Columns Read Without Explicit Type Casting

**Severity**: RED (Critical)
**File**: `src/datapulse/bronze/loader.py:78`

```python
df = pl.read_excel(file_path, engine="calamine")
```

**Why wrong**: `pl.read_excel()` with calamine infers column types from the Excel cell format. Financial columns (`Net Sales`, `Gross Sales`, `Quantity`, etc.) may be inferred as `Float64` instead of `Decimal`. The DB schema uses `NUMERIC(18,4)` but:
1. Float64 introduces IEEE 754 rounding errors on financial amounts (e.g., `13.2` may become `13.199999999999999`).
2. If any financial cell contains text (e.g., "N/A", "-", Arabic text), the entire column may be inferred as `Utf8` (string), and the INSERT will fail with a type mismatch or silently truncate.

There is no post-read type validation or casting step between `read_excel` and `load_to_postgres`.

**Fix**: Add explicit schema or post-read casting:
```python
FINANCIAL_COLS = ["net_sales", "gross_sales", "quantity", "sales_not_tax",
                  "dis_tax", "tax", "paid", "kzwi1", "subtotal5_discount", "add_dis"]

for col in FINANCIAL_COLS:
    if col in df.columns:
        df = df.with_columns(pl.col(col).cast(pl.Decimal(18, 4), strict=False))
```

**Test to add**: Unit test with a mock Excel file containing mixed-type financial cells, asserting they are correctly cast to Decimal.

---

### YELLOW-1: Materialization Conflict — `dbt_project.yml` vs `bronze_sales.sql`

**Severity**: YELLOW (Warning)
**File**: `dbt/dbt_project.yml:33-35` vs `dbt/models/bronze/bronze_sales.sql:2-5`

```yaml
# dbt_project.yml
models:
  datapulse:
    bronze:
      +materialized: table   # <-- says TABLE
```

```sql
-- bronze_sales.sql
{{ config(materialized='view', schema='bronze') }}  -- overrides to VIEW
```

**Why wrong**: The project-level config says bronze models should be `table`, but the model overrides to `view`. This is confusing for anyone reading `dbt_project.yml` expecting bronze to be a table. The model-level config wins (correct dbt behavior), but the project config is misleading.

**Fix**: Align `dbt_project.yml` to match reality:
```yaml
bronze:
  +materialized: view
```

---

### YELLOW-2: `_bronze__sources.yml` Documents Only 16 of 47 Columns

**Severity**: YELLOW (Warning)
**File**: `dbt/models/bronze/_bronze__sources.yml:18-51`

**Why wrong**: The source definition lists 16 columns but `bronze.sales` has 47 columns (per migration 001 + tenant_id from migration 003). Missing documentation for 31 columns including all financial columns (`gross_sales`, `subtotal5_discount`, `tax`, etc.), classification columns (`subcategory`, `division`, `segment`), and personnel columns.

This incomplete documentation means:
- `dbt docs generate` produces an incomplete data dictionary
- New team members have no reference for undocumented columns
- Freshness checks work (they only need `loaded_at`), but schema drift detection is weaker

**Fix**: Add all 47 columns to the sources YAML with descriptions.

---

### YELLOW-3: No dbt Tests on Bronze Source

**Severity**: YELLOW (Warning)
**File**: `dbt/models/bronze/_bronze__sources.yml`

**Why wrong**: Zero `tests:` blocks on any bronze source column. At minimum, the following should be tested:
- `id`: `unique`, `not_null`
- `source_file`: `not_null`
- `source_quarter`: `not_null`
- `date`: `not_null`
- `loaded_at`: `not_null`
- `tenant_id`: `not_null`

Without these, `dbt test --select source:bronze` does nothing — schema regressions go undetected.

**Fix**: Add tests to `_bronze__sources.yml`:
```yaml
columns:
  - name: id
    tests:
      - unique
      - not_null
  - name: source_file
    tests:
      - not_null
  - name: date
    tests:
      - not_null
  - name: tenant_id
    tests:
      - not_null
```

---

### YELLOW-4: Duplicate Mapping Target in `column_map.py`

**Severity**: YELLOW (Warning)
**File**: `src/datapulse/bronze/column_map.py:48,54`

```python
"Billing Type2": "billing_type2",
# ...
"Billing Type_1": "billing_type2",   # Polars auto-renames duplicate headers
```

**Why wrong**: Two Excel header variants map to the same DB column `billing_type2`. If an Excel file contains **both** "Billing Type2" and "Billing Type_1" (unlikely but possible), the rename step in `rename_columns()` would process both mappings. Since Polars `rename()` is applied as a dict, whichever key comes last in iteration order wins. The comment explains the intent (Polars auto-renames duplicates), but there's no guard against both existing simultaneously.

**Fix**: Add a log warning or assertion in `rename_columns()` if both headers are present:
```python
if "Billing Type2" in df.columns and "Billing Type_1" in df.columns:
    log.warning("duplicate_billing_type_headers", file="...")
```

---

### YELLOW-5: `discover_files()` Only Finds `.xlsx` — CSV Not Supported

**Severity**: YELLOW (Warning)
**File**: `src/datapulse/bronze/loader.py:50`

```python
for f in sorted(source_dir.rglob("*.xlsx")):
```

**Why wrong**: The project overview states "import raw Excel/CSV files", but the loader only discovers `.xlsx` files. Any `.csv` files in the source directory are silently ignored. The `read_single_file()` function also only calls `pl.read_excel()`, not `pl.read_csv()`.

**Fix**: Either:
1. Update docs to clarify only `.xlsx` is supported, or
2. Extend `discover_files()` to also glob `*.csv` and branch in `read_single_file()` based on suffix.

---

### YELLOW-6: Hardcoded Default Paths in Config

**Severity**: YELLOW (Warning)
**File**: `src/datapulse/core/config.py:58-60`

```python
dbt_project_dir: str = "/app/dbt"
dbt_profiles_dir: str = "/app/dbt"
raw_sales_path: str = "/app/data/raw/sales"
```

**Why wrong**: These are Docker container paths baked as defaults. Running outside Docker (local dev, CI) requires setting all three env vars. Not a bug in production, but a local-development footgun. The loader itself takes `--source` as a CLI arg, so it's not affected directly, but `PipelineExecutor.run_bronze()` uses `self._settings.raw_sales_path` (via pipeline routes).

**Fix**: Consider relative defaults or `None` with explicit error messages when unset outside Docker.

---

### YELLOW-7: No `loaded_at` Per-Run Tagging

**Severity**: YELLOW (Warning)
**File**: `migrations/001_create_bronze_schema.sql:9`

```sql
loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
```

Combined with `src/datapulse/bronze/loader.py:165`:
```python
db_columns = [col for col in df.columns if col not in ("id", "loaded_at")]
```

**Why wrong**: `loaded_at` uses `DEFAULT now()` and is excluded from the INSERT column list. Within a single transaction (`engine.begin()`), all rows get the same timestamp. This is fine for lineage — but combined with the broken rollback (RED-2), there's no reliable way to identify and delete rows from a specific pipeline run.

**Fix**: Already addressed by RED-2 fix (add `_pipeline_run_id`). As an additional measure, explicitly set `loaded_at` from Python with a run-start timestamp so it's deterministic.

---

### GREEN-1: Column Naming — `personel_number` Typo Preserved

**Severity**: GREEN (Suggestion)
**File**: `src/datapulse/bronze/column_map.py:14`, `migrations/001_create_bronze_schema.sql:49`

```python
"Personel Number": "personel_number",  # column_map.py
```
```sql
personel_number TEXT,  -- migration
```

**Why wrong**: "Personel" is a typo of "Personnel". The typo originates from the Excel source header, and bronze correctly preserves it as-is (bronze = raw). Silver renames it to `staff_id` (`stg_sales.sql:149`). No functional impact, but it's a confusing name for anyone querying bronze directly.

**Fix** (optional): If bronze is queried directly by analysts, consider adding a comment on the column explaining the intentional typo preservation:
```sql
COMMENT ON COLUMN bronze.sales.personel_number IS 'Personnel number — typo preserved from source Excel header';
```

---

### GREEN-2: Missing Composite Index for Silver Dedup Performance

**Severity**: GREEN (Suggestion)
**File**: `migrations/001_create_bronze_schema.sql:79-87`

**Why wrong**: The silver model deduplicates on `(tenant_id, reference_no, date, material, customer, site, quantity)` with `ORDER BY id`. There is no composite index matching this partition key. For 2.27M rows, the `ROW_NUMBER()` window function must do a full table sort.

**Fix**: Add a composite index:
```sql
CREATE INDEX IF NOT EXISTS idx_bronze_sales_dedup_key
    ON bronze.sales (tenant_id, reference_no, date, material, customer, site, quantity, id);
```

---

### GREEN-3: Source Freshness Thresholds May Be Too Loose

**Severity**: GREEN (Suggestion)
**File**: `dbt/models/bronze/_bronze__sources.yml:11-16`

```yaml
freshness:
  warn_after:
    count: 48
    period: hour
  error_after:
    count: 96
    period: hour
```

**Why wrong**: 48-hour warn / 96-hour error means data can be up to 4 days stale before an error. For a sales analytics platform, this may be acceptable for quarterly imports but too loose for real-time dashboards. Worth reviewing against the actual ingestion SLA.

**Fix**: Align thresholds with actual business SLA. If imports are quarterly, 96 hours is fine. If daily, consider tightening to 24h warn / 48h error.

---

### GREEN-4: `read_and_concat` Uses `diagonal_relaxed` — Schema Drift Between Files Is Silent

**Severity**: GREEN (Suggestion)
**File**: `src/datapulse/bronze/loader.py:125`

```python
combined = pl.concat(frames, how="diagonal_relaxed")
```

**Why wrong**: `diagonal_relaxed` fills missing columns with nulls and coerces mismatched types. If one quarter's Excel file has a new column or changes a column type, this is silently absorbed. For bronze (raw data), this is arguably correct behavior — but there's no logging of schema differences between files.

**Fix**: Log column set differences between frames before concat:
```python
all_cols = [set(f.columns) for f in frames]
if len(set(frozenset(c) for c in all_cols)) > 1:
    log.warning("schema_mismatch_between_files", ...)
```

---

### GREEN-5: Seeds Contain Arabic Text — Encoding Not Explicitly Set

**Severity**: GREEN (Suggestion)
**File**: `dbt/seeds/seed_budget_2025.csv`

```csv
2025,1,شبرا الخيمة,Pharma,3337237.1
```

**Why wrong**: The CSV contains Arabic site names. dbt seeds rely on the file being valid UTF-8. Most modern tools handle this correctly, but if the file is ever saved with a different encoding (e.g., Windows-1256), the Arabic text will be corrupted. There is no explicit encoding declaration or CI check.

**Fix**: Add a CI step or pre-commit hook that validates all `.csv` files are UTF-8 encoded.

---

## Summary Table

| ID | Severity | Finding | File |
|----|----------|---------|------|
| RED-1 | Critical | No idempotency — duplicate rows on re-run | `loader.py:176-185` |
| RED-2 | Critical | Rollback uses non-existent `_pipeline_run_id` column | `rollback.py:28` |
| RED-3 | Critical | No unique constraint on business keys | `001_create_bronze_schema.sql` |
| RED-4 | Critical | `tenant_id` not in loader's allowed columns | `loader.py:26-29` |
| RED-5 | Critical | Dedup key includes `quantity` — may silently drop legit rows | `stg_sales.sql:78-83` |
| RED-6 | Critical | Financial columns read without explicit type casting | `loader.py:78` |
| YEL-1 | Warning | Materialization conflict: project says table, model says view | `dbt_project.yml` / `bronze_sales.sql` |
| YEL-2 | Warning | Source YAML documents 16/47 columns | `_bronze__sources.yml` |
| YEL-3 | Warning | Zero dbt tests on bronze source columns | `_bronze__sources.yml` |
| YEL-4 | Warning | Duplicate mapping target for `billing_type2` | `column_map.py:48,54` |
| YEL-5 | Warning | Only `.xlsx` discovered, CSV silently skipped | `loader.py:50` |
| YEL-6 | Warning | Hardcoded Docker paths as defaults | `config.py:58-60` |
| YEL-7 | Warning | No per-run tagging (`loaded_at` + no `_pipeline_run_id`) | `001_create_bronze_schema.sql:9` |
| GRN-1 | Suggestion | `personel_number` typo preserved without comment | `column_map.py:14` |
| GRN-2 | Suggestion | Missing composite index for silver dedup performance | `001_create_bronze_schema.sql` |
| GRN-3 | Suggestion | Source freshness thresholds may be too loose | `_bronze__sources.yml:11-16` |
| GRN-4 | Suggestion | `diagonal_relaxed` concat silently absorbs schema drift | `loader.py:125` |
| GRN-5 | Suggestion | Arabic CSV seeds — no explicit UTF-8 validation | `seed_budget_2025.csv` |

---

## Top 3 Fixes for Bronze

### 1. Add Idempotency to the Bronze Loader (RED-1 + RED-3)

**Impact**: Prevents unbounded data duplication, enables safe re-runs.
**Action**: Implement quarter-scoped delete-before-insert in `load_to_postgres()`. Add a composite unique index on business keys as a safety net. This is the single highest-impact fix — it addresses both RED-1 and RED-3 simultaneously.

### 2. Fix Rollback by Adding `_pipeline_run_id` Column (RED-2 + YEL-7)

**Impact**: Enables per-run rollback and audit trail. Currently, rollback is completely broken.
**Action**: New migration to add `_pipeline_run_id UUID` to `bronze.sales`. Update `loader.py` to accept and insert `run_id`. Update `ALLOWED_COLUMNS`. Fix `rollback.py` to actually work. This also fixes YEL-7 (no per-run tagging).

### 3. Add Explicit Type Casting for Financial Columns (RED-6)

**Impact**: Prevents float precision loss on financial data and guards against mixed-type Excel columns.
**Action**: After `read_excel()`, cast all 10 financial columns to `pl.Decimal(18, 4)` with `strict=False`. Log any cast failures. Add a unit test with a mock Excel file containing edge-case values.
