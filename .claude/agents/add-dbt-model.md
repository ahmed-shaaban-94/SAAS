---
name: add-dbt-model
description: "Create a new dbt aggregation or dimension model with schema, tests, and RLS. Usage: /add-dbt-model <type> <name> <description>"
---

You are building a new dbt model for DataPulse. Follow these steps exactly:

## Input
Parse the user's request for:
- **type**: `agg` (aggregation), `dim` (dimension), or `fact`
- **name**: model name (e.g., `agg_sales_by_region`)
- **description**: what this model calculates

## Steps

### 1. Identify upstream models
Read existing marts models to understand available tables:
```
dbt/models/marts/dims/
dbt/models/marts/facts/fct_sales.sql
dbt/models/marts/aggs/
```
Determine which `{{ ref() }}` sources are needed.

### 2. Create the SQL model
Create file at `dbt/models/marts/<type>s/<name>.sql`:

```sql
{{ config(materialized='table', schema='marts') }}

WITH base AS (
    SELECT ...
    FROM {{ ref('fct_sales') }} f
    JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    -- Add other joins as needed
)
SELECT
    -- Group-by dimensions
    -- Aggregations: SUM, COUNT, COUNT(DISTINCT ...), AVG
    tenant_id  -- REQUIRED for RLS
FROM base
GROUP BY <dimensions>, tenant_id
```

Rules:
- Always include `tenant_id` in SELECT and GROUP BY
- Use `COALESCE(..., 0)` for nullable aggregations
- Use `{{ ref() }}` for all table references
- Follow naming: `agg_` prefix for aggregations, `dim_` for dimensions

### 3. Create/update schema YAML
Add to `dbt/models/marts/<type>s/_<type>s__models.yml`:
- Model name and description
- Column definitions with descriptions
- Tests: `unique`, `not_null` on key columns, `relationships` for FKs

### 4. Validate
Run these commands:
```bash
cd /home/user/SAAS && docker exec datapulse-api dbt parse
```
If parse succeeds:
```bash
docker exec datapulse-api dbt run --select <name>
docker exec datapulse-api dbt test --select <name>
```

### 5. Report results
Show:
- File created
- Columns in the model
- Test results
- Any issues found

## Conventions
- Materialization: `table` for marts
- Schema: `marts` (becomes `public_marts` in DB)
- RLS is applied automatically via dbt_project.yml post-hooks
- Financial columns: use `SUM(net_amount)`, `SUM(gross_amount)` etc.
- Date grouping: join `dim_date` and group by `year_num`, `month_num`, or `date_key`
