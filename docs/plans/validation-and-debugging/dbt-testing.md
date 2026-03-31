# dbt Testing

Testing strategy for dbt models across the medallion architecture: bronze sources, staging (silver), and marts (gold).

## Current State (DONE)

- **Framework**: dbt-core + dbt-postgres
- **Tests**: ~40 schema tests + data tests
- **Models**: 1 staging + 6 dims + 1 fact + 8 aggs + 1 metrics
- **Schema files**: `_bronze__sources.yml`, `_staging__sources.yml`, `_dims__models.yml`, `_facts__models.yml`, `_aggs__models.yml`

## Running Tests

```bash
# All dbt tests
docker exec -it datapulse-app dbt test --project-dir /app/dbt --profiles-dir /app/dbt

# Tests for a specific model
docker exec -it datapulse-app dbt test --select stg_sales --project-dir /app/dbt --profiles-dir /app/dbt

# Tests for a schema/directory
docker exec -it datapulse-app dbt test --select marts.dims --project-dir /app/dbt --profiles-dir /app/dbt

# Single named test
docker exec -it datapulse-app dbt test --select test_name --project-dir /app/dbt --profiles-dir /app/dbt

# Run models then test
docker exec -it datapulse-app dbt build --project-dir /app/dbt --profiles-dir /app/dbt
```

## Test Types

### 1. Schema Tests (Generic)

Defined in YAML schema files. These are declarative column-level assertions.

| Test | Purpose | Example |
|------|---------|---------|
| `unique` | No duplicate values in column | `dim_customer.customer_key` |
| `not_null` | No NULL values in column | `fct_sales.sale_key` |
| `accepted_values` | Column contains only expected values | `dim_billing.billing_group` |
| `relationships` | Foreign key integrity | `fct_sales.customer_key -> dim_customer.customer_key` |

Example from `_dims__models.yml`:

```yaml
models:
  - name: dim_customer
    columns:
      - name: customer_key
        tests:
          - unique
          - not_null
      - name: customer_name
        tests:
          - not_null
```

### 2. Data Tests (Custom SQL)

Custom SQL assertions in `dbt/tests/` directory. A test fails if the query returns any rows.

```sql
-- tests/assert_no_negative_net_sales.sql
SELECT *
FROM {{ ref('fct_sales') }}
WHERE net_sales < 0
  AND billing_type NOT IN ('returns', 'credit_note')
```

### 3. Source Freshness

Checks that source data is not stale.

```bash
docker exec -it datapulse-app dbt source freshness --project-dir /app/dbt --profiles-dir /app/dbt
```

Defined in `_bronze__sources.yml`:

```yaml
sources:
  - name: bronze
    tables:
      - name: sales
        loaded_at_field: _loaded_at
        freshness:
          warn_after: { count: 24, period: hour }
          error_after: { count: 48, period: hour }
```

## Model Coverage

### Staging (`stg_sales`)

| Test | Column | Status |
|------|--------|--------|
| `not_null` | `reference_no` | DONE |
| `not_null` | `date` | DONE |
| Deduplication check | (row count vs bronze) | DONE |
| Billing type EN mapping | `billing_type` | DONE |
| Derived field logic | Various | DONE |

### Dimensions

| Model | Tests | Key Assertions |
|-------|-------|---------------|
| `dim_date` | unique, not_null on `date_key` | 1,096 rows (2023-2025) |
| `dim_billing` | unique, not_null, accepted_values | 11 rows (10 types + Unknown) |
| `dim_customer` | unique, not_null on `customer_key` | Unknown member at key=-1 |
| `dim_product` | unique, not_null on `product_key` | Unknown member at key=-1 |
| `dim_site` | unique, not_null on `site_key` | Unknown member at key=-1 |
| `dim_staff` | unique, not_null on `staff_key` | Unknown member at key=-1 |

### Fact Table (`fct_sales`)

| Test | Column | Notes |
|------|--------|-------|
| `not_null` | All FK columns | COALESCE to -1 ensures no NULLs |
| `relationships` | All FK columns | Reference their dimension tables |
| `not_null` | `net_sales`, `gross_sales` | Financial measures always present |

### Aggregation Tables

| Model | Key Tests |
|-------|-----------|
| `agg_sales_daily` | not_null on date_key, unique on date_key |
| `agg_sales_monthly` | not_null, MoM/YoY calculations correct |
| `agg_sales_by_product` | not_null on product_key + month_key |
| `agg_sales_by_customer` | not_null on customer_key + month_key |
| `agg_sales_by_site` | not_null on site_key + month_key |
| `agg_sales_by_staff` | not_null on staff_key + month_key |
| `agg_returns` | not_null, return quantities positive |
| `metrics_summary` | not_null, MTD/YTD running totals non-negative |

## Recommended Additions (TODO)

### Row Count Assertions

- [ ] Add `dbt_utils.equal_rowcount` between related tables
- [ ] Add minimum row count assertions for critical tables

```yaml
# Requires dbt-utils package
tests:
  - dbt_utils.equal_rowcount:
      compare_model: ref('stg_sales')
```

### Referential Integrity Across Layers

- [ ] Verify every `fct_sales` FK resolves to a dimension row
- [ ] Verify agg tables sum to fct_sales totals (reconciliation)

```sql
-- tests/assert_agg_daily_matches_fact.sql
WITH fact_total AS (
    SELECT SUM(net_sales) AS total FROM {{ ref('fct_sales') }}
),
agg_total AS (
    SELECT SUM(net_sales) AS total FROM {{ ref('agg_sales_daily') }}
)
SELECT * FROM fact_total f
CROSS JOIN agg_total a
WHERE ABS(f.total - a.total) > 0.01
```

### Financial Precision Tests

- [ ] Verify NUMERIC(18,4) precision is maintained (no floating-point drift)
- [ ] Assert `gross_sales >= net_sales` where applicable

### Schema Drift Detection

- [ ] Compare expected column list against actual table schema
- [ ] Alert on unexpected columns or type changes

### Continuous Testing

- [ ] Run `dbt test` as part of pipeline execution (after each stage)
- [ ] This is partially done via quality gates in Phase 2.5
- [ ] Add `dbt build` (run + test) to the n8n pipeline workflow

## Test Development Checklist

1. Define expected behaviour in the schema YAML
2. Add `unique` and `not_null` on all primary keys
3. Add `relationships` for all foreign keys
4. Add `accepted_values` for enum-like columns
5. Write custom SQL tests for business logic assertions
6. Run `dbt test` and verify all pass
7. Check test results in the dbt log or `target/run_results.json`
