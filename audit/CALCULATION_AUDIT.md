# Calculation Audit Report

**Date:** 2026-04-07
**Files scanned:** 488 (135 Python, 35 dbt SQL/YAML, 280 Frontend TS/TSX, 15 Power BI TMDL, 23 Migrations)

## Summary

- 🔴 Critical: **15**
- 🟡 Warnings: **23**
- 🟢 Suggestions: **7**
- **Total findings: 45**

| Layer | 🔴 | 🟡 | 🟢 | Files |
|-------|-----|-----|-----|-------|
| Config & Thresholds | 0 | 2 | 1 | 5 |
| Pipeline & Forecasting | 1 | 3 | 1 | 6 |
| Python Analytics | 4 | 5 | 2 | 14 |
| dbt SQL Models | 6 | 7 | 2 | 26+7 |
| Frontend (Next.js) | 3 | 9 | 1 | 35 |
| Power BI DAX | 1 | 3 | 2 | 12 |

---

## LAYER 1: Config & Thresholds ✅

### Files Audited
- `src/datapulse/core/config.py`
- `src/datapulse/billing/plans.py`
- `src/datapulse/anomalies/models.py`
- `frontend/src/lib/constants.ts`
- `frontend/src/lib/health-thresholds.ts`

### Findings

#### 🟡 [C-1] Hardcoded anomaly detection thresholds not overridable per-tenant
- **File:** `src/datapulse/anomalies/models.py:15-19`
- **Severity:** Warning
- **Category:** Hardcoded magic numbers
- **Current code:**
  ```python
  class AnomalyDetectionConfig(BaseModel):
      critical_z: float = 3.5
      high_z: float = 3.0
      medium_z: float = 2.5
      low_z: float = 2.0
      lookback_days: int = 90
      min_data_points: int = 14
  ```
- **Why it matters:** All tenants share the same z-score thresholds. A pharmacy with highly seasonal sales (e.g., Ramadan) may need different thresholds than a stable one. These should be tenant-configurable or at least environment-variable driven.
- **Suggested fix:** Add `anomaly_` prefixed settings to `Settings` class or allow per-tenant overrides in DB.
- **Test to add:** `test_anomaly_thresholds_from_env` — verify env vars override defaults.

#### 🟡 [C-2] Health threshold `return_rate` inverted logic boundary is ambiguous
- **File:** `frontend/src/lib/health-thresholds.ts:25`
- **Severity:** Warning
- **Category:** Business logic clarity
- **Current code:**
  ```typescript
  return_rate: { goodAbove: 3, criticalBelow: 8, invertDirection: true },
  ```
- **Why it matters:** With `invertDirection: true`, `goodAbove: 3` means "good if value ≤ 3" and `criticalBelow: 8` means "critical if value ≥ 8". The naming `goodAbove` / `criticalBelow` is confusing when inverted — e.g., `goodAbove: 3` actually means "good if **below** 3". The unit is also implicit — is this 3% or 0.03? Given `return_rate` is sent as 0-1 from some endpoints and 0-100 from others (see H2 in previous audit), this is risky.
- **Suggested fix:** Add comments documenting expected unit (percentage 0-100), or rename to `goodThreshold` / `criticalThreshold`.

#### 🟢 [C-3] Forecast config is well-structured but `min_clamp: 0.01` could mask zero-revenue forecasts
- **File:** `src/datapulse/core/config.py:25`
- **Severity:** Suggestion
- **Category:** Business logic
- **Current code:**
  ```python
  min_clamp: float = 0.01
  ```
- **Why it matters:** Holt-Winters clamps near-zero values to 0.01 to avoid log issues. For products with genuinely zero sales, this creates a non-zero forecast. Acceptable trade-off but worth documenting.

### Files with no issues found
- `src/datapulse/billing/plans.py` — clean plan definitions, proper defaults
- `frontend/src/lib/constants.ts` — chart colors and nav, no calculations

---

## LAYER 2: Pipeline, Quality Gates & Forecasting ✅

### Files Audited
- `src/datapulse/pipeline/quality.py`
- `src/datapulse/forecasting/methods.py`
- `src/datapulse/anomalies/detector.py`
- `src/datapulse/targets/repository.py`
- `src/datapulse/api/filters.py`
- `src/datapulse/analytics/comparison_repository.py`

### Findings

#### 🔴 [PQ-1] IQR quartile computation uses naive indexing — incorrect for small N
- **File:** `src/datapulse/anomalies/detector.py:83-84`
- **Severity:** Critical
- **Category:** Incorrect statistical calculation
- **Current code:**
  ```python
  sorted_vals = sorted(values)
  n = len(sorted_vals)
  q1 = sorted_vals[n // 4]
  q3 = sorted_vals[3 * n // 4]
  ```
- **Why it's wrong:** For n=5: Q1 = sorted_vals[1], Q3 = sorted_vals[3]. Standard IQR uses interpolated quartiles (e.g., `statistics.quantiles()`). With n=14 (the minimum): Q1 = sorted_vals[3], Q3 = sorted_vals[10] — this is off from the true 25th/75th percentile which should interpolate between elements. For small samples (14-30 values), this can shift the IQR bounds significantly, causing missed anomalies or false positives.
- **Suggested fix:**
  ```python
  import statistics
  q1, _, q3 = statistics.quantiles(sorted_vals, n=4)
  iqr = q3 - q1
  ```
- **Test to add:** `test_iqr_quartiles_small_n` — compare detector IQR vs `statistics.quantiles` for n=14,15,16.

#### 🟡 [PQ-2] Population vs sample std dev inconsistency between detector and forecasting
- **File:** `src/datapulse/forecasting/methods.py:161` and `src/datapulse/anomalies/detector.py:39`
- **Severity:** Warning
- **Category:** Inconsistent statistical method
- **Current code:**
  ```python
  # forecasting/methods.py:161 — population std dev (/ N)
  std_val = (sum((x - mean_val) ** 2 for x in tail) / len(tail)) ** 0.5

  # anomalies/detector.py:39 — sample std dev (/ N-1) via statistics.stdev
  stdev = _stats.stdev(values)
  ```
- **Why it matters:** `statistics.stdev` uses Bessel's correction (N-1 denominator), while the SMA forecaster uses N. For n=30, the difference is ~1.7%. For n=7 (SMA window), it's ~8%. This means confidence intervals from SMA are slightly tighter than they should be.
- **Suggested fix:** Use `statistics.pstdev()` if population is intended, or switch both to `statistics.stdev()` for consistency.

#### 🟡 [PQ-3] Filter BETWEEN comparison uses lexicographic ordering for numeric fields
- **File:** `src/datapulse/api/filters.py:159`
- **Severity:** Warning
- **Category:** Type coercion bug
- **Current code:**
  ```python
  if low > high:
      low, high = high, low
  conditions.append(col.between(low, high))
  ```
- **Why it's wrong:** `low` and `high` are strings from URL query params. For numeric fields like `net_sales`, `"9" > "10"` is `True` lexicographically, so `?filter[net_sales][between]=9,10` would swap to `between(10, 9)` — the wrong direction. The actual SQL `BETWEEN` would still work (PostgreSQL casts), but the swap logic is incorrect.
- **Suggested fix:**
  ```python
  # Try numeric comparison first, fall back to string
  try:
      if float(low) > float(high):
          low, high = high, low
  except ValueError:
      if low > high:
          low, high = high, low
  ```
- **Test to add:** `test_filter_between_numeric_swap` — verify `?filter[net_sales][between]=9,10` doesn't swap.

#### 🟡 [PQ-4] Seasonal naive forecast std dev uses abs(diffs) before squaring — inflated bounds
- **File:** `src/datapulse/forecasting/methods.py:199`
- **Severity:** Warning
- **Category:** Statistical method
- **Current code:**
  ```python
  diffs = [abs(a - b) for a, b in zip(last_cycle, prev_cycle, strict=True)]
  std_val = (sum(d**2 for d in diffs) / len(diffs)) ** 0.5
  ```
- **Why it matters:** Takes absolute value THEN squares. Since `abs(d)**2 == d**2`, the abs is redundant but misleading. The real issue is this computes RMSD (root mean square difference between two cycles) and uses it as standard deviation for confidence intervals. This overestimates uncertainty because it conflates systematic trend with noise.
- **Suggested fix:** Remove `abs()` for clarity. Consider using signed differences and computing proper standard deviation.

#### 🟢 [PQ-5] Quality gate `check_null_rate` uses float multiplication in SQL
- **File:** `src/datapulse/pipeline/quality.py:252`
- **Severity:** Suggestion
- **Category:** Precision
- **Current code:**
  ```python
  f"(COUNT(*) FILTER (WHERE {col} IS NULL)) * 100.0 / NULLIF(COUNT(*), 0) AS {col}_null_pct"
  ```
- **Why it matters:** `100.0` produces float in PostgreSQL. For a 5% threshold comparison, float precision is fine, but `100::NUMERIC` would be consistent with the project convention.

### Files with no issues found
- `src/datapulse/targets/repository.py` — clean Decimal arithmetic, proper division-by-zero guards on all achievement calculations
- `src/datapulse/analytics/comparison_repository.py` — correct growth logic: 0→X = +100%, X→0 = -100%, safe_growth for rest
- `src/datapulse/pipeline/quality.py` (besides PQ-5) — well-designed quality gates, proper column allowlisting

---

## LAYER 3: Python Analytics Backend ✅

### Files Audited
- `src/datapulse/analytics/repository.py` (1050+ lines)
- `src/datapulse/analytics/advanced_repository.py`
- `src/datapulse/analytics/breakdown_repository.py`
- `src/datapulse/analytics/detail_repository.py`
- `src/datapulse/analytics/queries.py`
- `src/datapulse/analytics/customer_health.py`
- `src/datapulse/analytics/hierarchy_repository.py`
- `src/datapulse/analytics/search_repository.py`
- `src/datapulse/analytics/diagnostics.py`
- `src/datapulse/analytics/models.py`
- `src/datapulse/analytics/service.py`
- `src/datapulse/explore/sql_builder.py`
- `src/datapulse/reports/template_engine.py`
- `src/datapulse/bronze/loader.py`

### Findings

#### 🔴 [PY-1] `daily_transactions` calculated inconsistently across 3 code paths
- **File:** `src/datapulse/analytics/repository.py:376` vs `:649` vs `:815`
- **Severity:** Critical
- **Category:** Inconsistent business metric
- **Current code:**
  ```python
  # Path A: metrics_summary (line 376) — includes returns
  daily_transactions=daily_transactions,  # raw COUNT(*) from DB

  # Path B: fct_sales fallback (line 649) — excludes returns
  daily_transactions=total_transactions - total_returns,

  # Path C: range query (line 815) — excludes returns
  daily_transactions=total_transactions - total_returns,
  ```
- **Why it's wrong:** `agg_sales_daily.transaction_count` = `COUNT(*)` which includes return rows. Path A passes this raw value. Paths B & C subtract `total_returns`. The same KPI endpoint can show 1,200 or 1,150 transactions for the same day depending on which path executes.
- **Suggested fix:**
  ```python
  # Path A: subtract returns to match B and C
  daily_transactions=daily_transactions - daily_returns,
  ```
- **Test to add:** `test_kpi_daily_transactions_excludes_returns` — assert all 3 paths produce the same value for known test data.

#### 🔴 [PY-2] Return rate unit inconsistency — 0-1 vs 0-100 across endpoints
- **File:** `src/datapulse/analytics/advanced_repository.py:192` vs `src/datapulse/analytics/detail_repository.py:336`
- **Severity:** Critical
- **Category:** Unit mismatch
- **Current code:**
  ```sql
  -- advanced_repository.py:192 → returns 0-100
  ROUND(AVG(return_rate) * 100, 2) AS return_rate

  -- detail_repository.py:336 → returns 0-1
  return_rate=Decimal(str(row["return_rate"])).quantize(Decimal("0.0001"))
  ```
- **Why it's wrong:** The `agg_sales_monthly.return_rate` stores 0-1 decimals (e.g., 0.0342 = 3.42%). The returns trend endpoint multiplies by 100, but detail endpoints don't. Frontend displaying raw 0.0342 as "0.03%" or multiplied 3.42 as "342%" depending on assumptions.
- **Suggested fix:** Standardize: always transmit as 0-1, multiply by 100 only in frontend display code.
- **Test to add:** `test_return_rate_unit_consistency` — assert all endpoints returning return_rate use the same unit range.

#### 🔴 [PY-3] Average return rate uses simple average instead of weighted by volume
- **File:** `src/datapulse/analytics/advanced_repository.py:219-221`
- **Severity:** Critical
- **Category:** Wrong aggregation method
- **Current code:**
  ```python
  avg_rate = (
      Decimal(sum(p.return_rate for p in points) / len(points)).quantize(Decimal("0.01"))
      if points else _ZERO
  )
  ```
- **Why it's wrong:** Averages monthly rates arithmetically. Jan: 100 txns, 5% return. Mar: 10,000 txns, 2% return. Simple avg = 3.5%. Correct weighted avg = 2.07%. The 69% overstatement makes return performance look worse than reality.
- **Suggested fix:**
  ```python
  total_returns = sum(p.return_count for p in points)
  total_txns = sum(p.return_count + ... for p in points)  # need transaction count
  avg_rate = Decimal(str(total_returns / total_txns * 100)).quantize(Decimal("0.01"))
  ```
- **Test to add:** `test_avg_return_rate_weighted` — 3 months with different volumes, verify weighted average.

#### 🔴 [PY-4] Origin breakdown returns `float` instead of `Decimal` for financial amounts
- **File:** `src/datapulse/analytics/repository.py:916-925`
- **Severity:** Critical
- **Category:** Float for money / API contract inconsistency
- **Current code:**
  ```python
  total = sum(float(r[1]) for r in rows)
  return [
      {
          "origin": str(r[0]),
          "value": float(r[1]),          # float — precision loss
          "pct": round(float(r[1]) / total * 100, 1) if total else 0,
      }
      for r in rows
  ]
  ```
- **Why it's wrong:** All other analytics endpoints use `Decimal` + `JsonDecimal`. This endpoint uses `float`, causing IEEE 754 artifacts (e.g., `1234567.8912000001` in JSON). Also uses 1-decimal rounding for pct while others use 2.
- **Suggested fix:** Use `Decimal(str(r[1]))` and return `JsonDecimal` values.
- **Test to add:** `test_origin_breakdown_returns_decimal` — assert response values are clean decimals.

#### 🟡 [PY-5] Transaction netting formula `- 2 * return_count` assumes each return has a matching sale
- **File:** `src/datapulse/analytics/breakdown_repository.py:50`
- **Severity:** Warning
- **Category:** Business logic assumption
- **Current code:**
  ```sql
  SUM(a.transaction_count) - 2 * SUM(a.return_count) AS transaction_count,
  ```
- **Why it matters:** `transaction_count = COUNT(*)` includes return rows. Subtracting `2 * return_count` removes both the return row AND its assumed original sale. If returns are standalone credit notes without a matching original transaction, this over-subtracts and can produce negative counts.
- **Suggested fix:** Document the assumption. If standalone returns exist, use `SUM(a.transaction_count) - SUM(a.return_count)` instead.

#### 🟡 [PY-6] Silent fallback when all breakdown values are negative
- **File:** `src/datapulse/analytics/breakdown_repository.py:64`
- **Severity:** Warning
- **Category:** Silent data quality issue
- **Current code:**
  ```python
  grand_total = sum(v for _, _, v in raw) or Decimal("1")
  ```
- **Why it matters:** If all sales are returns (net negative), the `or` triggers and sets `grand_total = 1`, making percentages meaningless (e.g., -50,000 / 1 * 100 = -5,000,000%). Should return an explicit error or zero-state.

#### 🟡 [PY-7] `safe_growth()` returns None for zero-to-nonzero growth (new entrants)
- **File:** `src/datapulse/analytics/queries.py:119-123`
- **Severity:** Warning
- **Category:** Edge case handling
- **Current code:**
  ```python
  def safe_growth(current: Decimal, previous: Decimal) -> Decimal | None:
      if previous == _ZERO:
          return None
      return ((current - previous) / previous * 100).quantize(Decimal("0.01"))
  ```
- **Why it matters:** `comparison_repository.py` correctly handles this by treating None as +100% for new entrants. But other callers (KPI, detail pages) may display "N/A" instead of a meaningful value. The contract should be documented.

#### 🟡 [PY-8] `other_count` can go negative without validation
- **File:** `src/datapulse/analytics/breakdown_repository.py:106`
- **Severity:** Warning
- **Category:** Missing validation
- **Current code:**
  ```python
  other_count=int(r[3]) - int(r[1]) - int(r[2]),
  ```
- **Why it matters:** `total_count - walk_in_count - insurance_count` assumes these three are exhaustive. Data quality issues could make walk_in + insurance > total, producing negative `other_count`.
- **Suggested fix:** `max(int(r[3]) - int(r[1]) - int(r[2]), 0)`

#### 🟡 [PY-9] Percentage rounding inconsistency across analytics endpoints
- **File:** Multiple files
- **Severity:** Warning
- **Category:** API inconsistency
- **Details:**
  | File | Line | Precision |
  |------|------|-----------|
  | `queries.py` | 238 | 2 decimals (`Decimal("0.01")`) |
  | `repository.py` | 922 | 1 decimal (`round(..., 1)`) |
  | `detail_repository.py` | 336 | 4 decimals (`Decimal("0.0001")`) |
  | `breakdown_repository.py` | 66 | 2 decimals (`Decimal("0.01")`) |
- **Suggested fix:** Standardize all percentage fields to 2 decimal places.

#### 🟢 [PY-10] Coefficient of variation silently returns None for zero-mean distributions
- **File:** `src/datapulse/analytics/queries.py:188-204`
- **Severity:** Suggestion
- **Category:** Edge case documentation
- **Current code:**
  ```python
  if mean == 0:
      return None
  ```
- **Why it matters:** Correct behavior mathematically (CV undefined for zero mean), but callers should know None means "undefined", not "zero variation". Add docstring clarification.

#### 🟢 [PY-11] Staff activity threshold (33% of average) is hardcoded magic number
- **File:** `src/datapulse/analytics/repository.py:988` and `src/datapulse/analytics/comparison_repository.py:101`
- **Severity:** Suggestion
- **Category:** Hardcoded magic number
- **Current code:**
  ```sql
  SELECT COALESCE(AVG(sale_count) * 0.33, 0) AS min_txns FROM staff_txns
  ```
- **Why it matters:** The 0.33 threshold is duplicated in two files. Should be a named constant.
- **Suggested fix:** Add `STAFF_ACTIVITY_THRESHOLD = Decimal("0.33")` to `queries.py`.

### Files with no issues found
- `src/datapulse/analytics/models.py` — Pydantic models are well-typed with `JsonDecimal`
- `src/datapulse/analytics/service.py` — caching wrapper, no calculations
- `src/datapulse/analytics/customer_health.py` — delegates to SQL, no Python-side math
- `src/datapulse/analytics/hierarchy_repository.py` — clean hierarchy queries
- `src/datapulse/analytics/search_repository.py` — text search, no calculations
- `src/datapulse/analytics/diagnostics.py` — diagnostic queries, no math
- `src/datapulse/explore/sql_builder.py` — well-secured SQL builder with whitelist
- `src/datapulse/reports/template_engine.py` — template rendering, no math
- `src/datapulse/bronze/loader.py` — data loading, correct batch progress calculation

---

## LAYER 4: dbt SQL Models ✅

### Files Audited
- `dbt/models/staging/stg_sales.sql`
- `dbt/models/bronze/bronze_sales.sql`
- `dbt/models/marts/facts/fct_sales.sql`
- `dbt/models/marts/dims/dim_date.sql`, `dim_customer.sql`, `dim_product.sql`, `dim_staff.sql`, `dim_site.sql`, `dim_billing.sql`
- `dbt/models/marts/aggs/agg_sales_daily.sql`, `agg_sales_monthly.sql`, `agg_sales_by_customer.sql`, `agg_sales_by_product.sql`, `agg_sales_by_staff.sql`, `agg_sales_by_site.sql`, `agg_returns.sql`, `metrics_summary.sql`
- `dbt/models/marts/features/feat_customer_segments.sql`, `feat_customer_health.sql`, `feat_product_lifecycle.sql`, `feat_revenue_daily_rolling.sql`, `feat_revenue_site_rolling.sql`, `feat_seasonality_daily.sql`, `feat_seasonality_monthly.sql`
- `dbt/macros/governorate_map.sql`
- `dbt/tests/assert_unknown_dimension_below_threshold.sql`
- All schema YAML files

### Findings

#### 🟡 [DBT-1] `feat_customer_health.sql` recomputes weighted health score 5 times in CASE WHEN
- **File:** `dbt/models/marts/features/feat_customer_health.sql:160-173`
- **Severity:** Warning
- **Category:** Repeated calculation / maintainability risk
- **Current code:**
  ```sql
  -- Line 160: computed once
  (recency_score * 0.30 + frequency_score * 0.25 + monetary_score * 0.25
   + return_score * 0.10 + diversity_score * 0.10) AS health_score,

  -- Lines 169-173: recomputed 4 times in CASE WHEN
  CASE
    WHEN (recency_score * 0.30 + ...) >= 80 THEN 'Excellent'
    WHEN (recency_score * 0.30 + ...) >= 60 THEN 'Good'
    WHEN (recency_score * 0.30 + ...) >= 40 THEN 'Fair'
    ELSE 'Poor'
  END AS health_band
  ```
- **Why it matters:** The exact same 5-term weighted formula is written 5 times. If weights change (e.g., recency from 0.30 to 0.35), all 5 must be updated. One missed update = wrong health band classification. PostgreSQL cannot reference a column alias in the same SELECT.
- **Suggested fix:** Wrap in a CTE:
  ```sql
  , scored AS (
    SELECT *, (recency_score * 0.30 + ...) AS health_score
    FROM ...
  )
  SELECT *,
    CASE WHEN health_score >= 80 THEN 'Excellent' ... END AS health_band
  FROM scored
  ```
- **Test to add:** `test_health_band_matches_health_score` — verify band thresholds match score.

#### 🟡 [DBT-2] Quantity precision inconsistency: `NUMERIC(18,4)` vs `ROUND(..., 2)` across aggregations
- **File:** `dbt/models/marts/aggs/agg_sales_daily.sql:28` vs `agg_sales_by_site.sql:30` vs `agg_sales_by_staff.sql:30`
- **Severity:** Warning
- **Category:** Inconsistent precision
- **Current code:**
  ```sql
  -- agg_sales_daily.sql:28 — 4 decimal precision
  SUM(f.quantity)::NUMERIC(18,4) AS total_quantity,

  -- agg_sales_by_site.sql:30 — 2 decimal precision
  ROUND(SUM(f.quantity)::NUMERIC, 2) AS total_quantity,

  -- agg_sales_by_staff.sql:30 — 2 decimal precision
  ROUND(SUM(f.quantity)::NUMERIC, 2) AS total_quantity,
  ```
- **Why it matters:** If a product has quantity 0.3333 per unit, the daily agg preserves it as 0.3333 but site/staff aggs round to 0.33. Month-level totals could differ by up to 0.005 per row × thousands of rows.
- **Suggested fix:** Use `SUM(f.quantity)::NUMERIC(18,4)` everywhere.

#### 🟡 [DBT-3] `agg_sales_monthly.return_rate` has no dbt test — no bounds, no not_null
- **File:** `dbt/models/marts/aggs/_aggs__models.yml:167-168`
- **Severity:** Warning
- **Category:** Missing dbt test for critical business metric
- **Current code:**
  ```yaml
  - name: return_rate
    description: "Ratio of returns to total transactions"
    # NO TESTS
  ```
- **Why it matters:** `return_rate` is consumed by multiple Python endpoints, some multiplying by 100, some not (see PY-2). A NULL or negative return_rate would cascade through the analytics layer silently.
- **Suggested fix:** Add tests:
  ```yaml
  - name: return_rate
    tests:
      - dbt_utils.accepted_range:
          min_value: 0
          max_value: 1
          inclusive: true
  ```
- **Test to add:** Singular test asserting no return_rate exceeds 1.0 or is negative.

#### 🔴 [DBT-7] `metrics_summary` incremental run corrupts MTD/YTD running totals
- **File:** `dbt/models/marts/aggs/metrics_summary.sql:67-109,111-113`
- **Severity:** Critical
- **Category:** Silent data corruption
- **Current code:**
  ```sql
  -- Line 67-73: MTD window function
  SUM(t.daily_gross_amount) OVER (
      PARTITION BY t.tenant_id, t.year, t.month
      ORDER BY t.full_date
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS mtd_gross_amount,
  ...
  -- Line 111-113: Incremental filter
  {% if is_incremental() %}
  WHERE t.full_date >= CURRENT_DATE - INTERVAL '3 days'
  {% endif %}
  ```
- **Why it's wrong:** During incremental runs, the WHERE clause filters to only the last 3 days. The window functions (`PARTITION BY year, month ... UNBOUNDED PRECEDING`) then operate only on this 3-day subset. On March 29, MTD should sum March 1–29 but instead sums only March 27–29. YTD is even worse — it should sum Jan 1–Mar 29 but only sees 3 days.
  - **Concrete example:** If March has 29 days with ~100K EGP/day, the correct MTD is ~2.9M EGP. The incremental run produces ~300K EGP (3 days only). This silently overwrites the correct values via `unique_key`.
- **Suggested fix:** Expand the incremental window to include the full month-to-date (or full year-to-date for YTD):
  ```sql
  {% if is_incremental() %}
  WHERE t.full_date >= DATE_TRUNC('year', CURRENT_DATE)
  {% endif %}
  ```
  Or better: use a two-step approach — filter the CTE to recent data but join back to get the full window context.
- **Test to add:** Singular test: compare MTD on last day of month vs SUM of daily values for that month.

#### 🔴 [DBT-8] `dim_date.year_week` uses `EXTRACT(YEAR)` instead of `EXTRACT(ISOYEAR)` — wrong at year boundaries
- **File:** `dbt/models/marts/dims/dim_date.sql:37`
- **Severity:** Critical
- **Category:** Incorrect date logic
- **Current code:**
  ```sql
  EXTRACT(YEAR FROM full_date)::INT || '-W' || LPAD(EXTRACT(WEEK FROM full_date)::INT::TEXT, 2, '0')
                                                AS year_week,
  ```
- **Why it's wrong:** `EXTRACT(WEEK ...)` returns ISO 8601 week numbers (1–53), but the year prefix uses `EXTRACT(YEAR ...)` (calendar year). At year boundaries, ISO week 1 of 2025 may include Dec 29–31 of 2024. Those dates produce `"2024-W01"` instead of `"2025-W01"`.
  - **Concrete example:** 2024-12-30 is ISO week 1 of 2025. Current code: `"2024-W01"`. Correct: `"2025-W01"`. Grouping by `year_week` would mix Dec 30, 2024 with Jan 6, 2025 (actual W01 of 2024).
- **Suggested fix:**
  ```sql
  EXTRACT(ISOYEAR FROM full_date)::INT || '-W' || LPAD(EXTRACT(WEEK FROM full_date)::INT::TEXT, 2, '0')
                                                AS year_week,
  ```
- **Test to add:** `test_year_week_iso_boundary` — assert that Dec 29-31, 2024 produce `"2025-W01"`.

#### 🔴 [DBT-9] `agg_sales_monthly` computes `total_net_amount` but drops it from final SELECT
- **File:** `dbt/models/marts/aggs/agg_sales_monthly.sql:31,64-91`
- **Severity:** Critical
- **Category:** Missing column / YAML test failure
- **Current code:**
  ```sql
  -- Line 31 (in monthly_base CTE): computed
  ROUND(SUM(f.net_amount), 2)  AS total_net_amount,

  -- Lines 64-91 (final SELECT): NOT included
  SELECT g.total_quantity, g.total_sales, g.total_discount,
         g.transaction_count, ...
  -- total_net_amount is missing from this list
  ```
- **Why it's wrong:** The YAML schema (`_aggs__models.yml:155-158`) defines `total_net_amount` with a `not_null` test. Since the column is absent from the SQL output, `dbt test` would fail. Any downstream model or API query referencing `agg_sales_monthly.total_net_amount` would error.
- **Suggested fix:** Add `g.total_net_amount,` to the final SELECT between `g.total_discount,` and `g.transaction_count,`.
- **Test to add:** Already defined in YAML — fix the SQL so the existing test passes.

#### 🔴 [DBT-10] `agg_sales_by_site` missing `total_net_amount` column entirely
- **File:** `dbt/models/marts/aggs/agg_sales_by_site.sql:22-65`
- **Severity:** Critical
- **Category:** Missing column / YAML test failure
- **Current code:**
  ```sql
  -- site_monthly CTE computes:
  total_quantity, total_sales, total_discount, transaction_count, ...
  -- NO SUM(f.net_amount) anywhere in the SQL
  ```
- **Why it's wrong:** YAML schema (`_aggs__models.yml:309-311`) defines `total_net_amount` with `not_null` test, but the SQL never computes it. `dbt test` would fail.
- **Suggested fix:** Add to `site_monthly` CTE:
  ```sql
  ROUND(SUM(f.net_amount)::NUMERIC, 2)  AS total_net_amount,
  ```
  And include in final SELECT.

#### 🔴 [DBT-11] `agg_sales_by_staff` missing `total_net_amount` column entirely
- **File:** `dbt/models/marts/aggs/agg_sales_by_staff.sql:22-52`
- **Severity:** Critical
- **Category:** Missing column / YAML test failure
- **Current code:**
  ```sql
  -- staff_monthly CTE computes:
  total_quantity, total_sales, total_discount, ...
  -- NO SUM(f.net_amount) anywhere in the SQL
  ```
- **Why it's wrong:** Same issue as DBT-10 — YAML defines `total_net_amount` with `not_null` test but SQL doesn't produce it.
- **Suggested fix:** Add `ROUND(SUM(f.net_amount)::NUMERIC, 2) AS total_net_amount,` to `staff_monthly` CTE and final SELECT.

#### 🔴 [DBT-12] `fct_sales` 32-bit hash surrogate key has ~149 expected collisions at 1.13M rows
- **File:** `dbt/models/marts/facts/fct_sales.sql:56-65`
- **Severity:** Critical
- **Category:** Data integrity / key collision
- **Current code:**
  ```sql
  ('x' || LEFT(MD5(
      COALESCE(s.tenant_id::TEXT, '') || '|' ||
      COALESCE(s.invoice_id, '') || '|' ||
      ... 8 fields ...
  ), 8))::BIT(32)::INT AS sales_key,
  ```
- **Why it's wrong:** `LEFT(MD5(...), 8)` takes 8 hex chars = 32 bits = 4.29 billion possible values. By the birthday paradox, with 1.13M rows: expected collisions ≈ n²/(2m) = (1.13×10⁶)² / (2×4.29×10⁹) ≈ **149 collisions**. Two different invoices sharing the same `sales_key` means:
  - Any `JOIN ON sales_key` produces duplicate rows
  - Any `DISTINCT sales_key` query loses rows silently
  - If used as `unique_key` in incremental models, one row overwrites another
- **Suggested fix:** Use full MD5 (128-bit) or at least 64-bit:
  ```sql
  ('x' || LEFT(MD5(...), 16))::BIT(64)::BIGINT AS sales_key,
  ```
  At 64 bits, expected collisions drop to ~0.00015 (essentially zero).
- **Test to add:** `test_fct_sales_no_duplicate_keys` — `SELECT sales_key, COUNT(*) FROM fct_sales GROUP BY sales_key HAVING COUNT(*) > 1`.

#### 🟡 [DBT-4] `metrics_summary.daily_transactions` includes returns — inconsistent with Python layer
- **File:** `dbt/models/marts/aggs/metrics_summary.sql:43`
- **Severity:** Warning
- **Category:** Business metric definition mismatch
- **Current code:**
  ```sql
  SUM(a.transaction_count)::INT AS daily_transactions,
  ```
- **Why it matters:** This is the root cause of PY-1. `transaction_count` in `agg_sales_daily` = `COUNT(*)` including return rows. The metrics_summary passes this value to the Python layer, which sometimes uses it as-is (including returns) and sometimes subtracts returns manually. The definition should be consistent at the SQL level.
- **Suggested fix:** Either: (a) rename to `daily_total_transactions` and add `daily_net_transactions = SUM(a.transaction_count) - SUM(a.return_count)`, or (b) define `daily_transactions` as net in the SQL.

#### 🟢 [DBT-5] `feat_revenue_daily_rolling` uses 364-day lag for YoY — correct but undocumented
- **File:** `dbt/models/marts/features/feat_revenue_daily_rolling.sql:100`
- **Severity:** Suggestion
- **Category:** Documentation
- **Current code:**
  ```sql
  LAG(r.daily_gross_amount, 364) OVER (...) AS same_day_last_year
  ```
- **Why it matters:** Uses 364 (52 weeks × 7) instead of 365 to align same day-of-week. This is correct business practice but should have a comment explaining why.

#### 🟡 [DBT-13] `feat_customer_health` percentile boundaries computed across all tenants
- **File:** `dbt/models/marts/features/feat_customer_health.sql:79-86`
- **Severity:** Warning
- **Category:** Multi-tenant leakage
- **Current code:**
  ```sql
  percentiles AS (
      SELECT
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY r.recency_days) AS recency_p95,
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ra.frequency_3m) AS freq_p95,
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ra.monetary_3m) AS monetary_p95,
          ...
      FROM recent_activity ra
      JOIN recency r ON ra.customer_key = r.customer_key
  )
  ```
- **Why it matters:** Percentile boundaries (p95) are computed across ALL tenants' customers together. A high-spend tenant (e.g., hospital pharmacy) skews `monetary_p95` upward, making all small-pharmacy customers score artificially low on monetary. Also, the model has no `tenant_id` column and no RLS post_hook, unlike all other marts models.
- **Suggested fix:** Add `PARTITION BY tenant_id` to percentile calculations, include `tenant_id` in output, add RLS post_hook.

#### 🟡 [DBT-14] `agg_returns` uses `ABS(SUM(...))` instead of `SUM(ABS(...))` — fragile for mixed-sign data
- **File:** `dbt/models/marts/aggs/agg_returns.sql:33-34`
- **Severity:** Warning
- **Category:** Fragile aggregation
- **Current code:**
  ```sql
  ABS(ROUND(SUM(f.quantity)::NUMERIC, 2))  AS return_quantity,
  ABS(ROUND(SUM(f.sales)::NUMERIC, 2))     AS return_amount,
  ```
- **Why it matters:** If return rows have mixed signs due to data quality issues (e.g., a correction entry with positive quantity among negative returns), `SUM()` partially cancels out, then `ABS()` hides the problem. `SUM(ABS(...))` would be more defensive and give the correct total return magnitude regardless of sign inconsistency.
- **Suggested fix:** `SUM(ABS(f.quantity))::NUMERIC(18,2) AS return_quantity`

#### 🟡 [DBT-15] `agg_sales_daily.avg_basket_size` documented as "net amount" but uses gross `f.sales`
- **File:** `dbt/models/marts/aggs/agg_sales_daily.sql:37` vs `_aggs__models.yml:108`
- **Severity:** Warning
- **Category:** Documentation vs code mismatch
- **Current code:**
  ```sql
  -- SQL (line 37):
  SUM(f.sales) / NULLIF(COUNT(DISTINCT f.invoice_id), 0) AS avg_basket_size
  ```
  ```yaml
  # YAML (line 108):
  - name: avg_basket_size
    description: "Average net amount per invoice"
  ```
- **Why it matters:** YAML says "net amount" but SQL uses `f.sales` (gross, before discount). The same pattern exists in `agg_sales_monthly.sql:40-42`. This misleads analysts who trust the documentation.
- **Suggested fix:** Either change SQL to `SUM(f.net_amount)` to match docs, or fix docs to say "Average gross sales per invoice".

#### 🟢 [DBT-6] All aggregation models use full table materialization — incremental could improve performance
- **File:** All `dbt/models/marts/aggs/*.sql`
- **Severity:** Suggestion
- **Category:** Performance
- **Why it matters:** With 2.27M bronze rows and 1.13M fact rows, full table refreshes on every dbt run could be slow. Models like `agg_sales_daily` and `metrics_summary` are good candidates for incremental materialization with `unique_key`.

### Verified Correct (no issues)
- **Division protection:** All dbt models use `NULLIF(denominator, 0)` consistently
- **Multi-tenant safety:** Most JOINs include `tenant_id`, most window functions `PARTITION BY tenant_id` (exception: DBT-13)
- **Financial precision:** Sales/discounts: `ROUND(..., 2)`, quantities: `NUMERIC(18,4)` (mostly — see DBT-2)
- **Window functions:** Correct `ROWS BETWEEN` frames in rolling features (exception: metrics_summary incremental — DBT-7)
- **Growth rates:** MoM/YoY in `agg_sales_monthly` use proper `NULLIF` protection
- **RFM NTILE scoring:** `feat_customer_segments.sql:56` — `ORDER BY days_since_last DESC` gives NTILE(1) to oldest (worst), NTILE(5) to most recent (best) — **CORRECT** (comment confirms: "Higher score = better")
- **Product lifecycle phases:** `feat_product_lifecycle.sql:94-104` — dormant quarter logic with `-1` buffer is **CORRECT** (provides 1-quarter grace period)
- **Customer health scores:** Recency/frequency/monetary/return/diversity scoring math is sound (weights and normalization correct)
- **Seasonality indices:** DOW and monthly divided by grand average, NULLIF protected
- **Rolling averages:** 7/30/90-day windows use `ROWS BETWEEN N-1 PRECEDING AND CURRENT ROW` — correct
- **Date dimension:** Egypt weekend (Fri/Sat) coded as `ISODOW IN (5, 6)` — correct (exception: year_week — DBT-8)
- **GROUP BY completeness:** All non-aggregated columns present in GROUP BY across all models
- **NULL handling:** `COALESCE` used properly for financial defaults, `FILTER (WHERE ...)` for conditional counts

---

## LAYER 5: Frontend (Next.js + TypeScript) ✅

### Files Audited
- `frontend/src/lib/formatters.ts`
- `frontend/src/lib/chart-utils.ts`
- `frontend/src/lib/health-thresholds.ts`
- `frontend/src/lib/date-utils.ts`
- `frontend/src/lib/utils.ts`
- `frontend/src/hooks/use-count-up.ts`
- `frontend/src/hooks/use-comparison-trend.ts`
- `frontend/src/hooks/use-date-range.ts`
- `frontend/src/components/dashboard/kpi-card.tsx`
- `frontend/src/components/dashboard/target-progress.tsx`
- `frontend/src/components/dashboard/calendar-heatmap.tsx`
- `frontend/src/components/dashboard/monthly-trend-chart.tsx`
- `frontend/src/components/dashboard/waterfall-chart.tsx`
- `frontend/src/components/dashboard/billing-breakdown-chart.tsx`
- `frontend/src/components/dashboard/customer-type-chart.tsx`
- `frontend/src/components/dashboard/day-hero.tsx`
- `frontend/src/components/dashboard/trend-kpi-cards.tsx`
- `frontend/src/components/dashboard/forecast-card.tsx`
- `frontend/src/components/comparison/comparison-kpi.tsx`
- `frontend/src/components/comparison/period-picker.tsx`
- `frontend/src/components/customers/health-dashboard.tsx`
- `frontend/src/components/customers/rfm-matrix.tsx`
- `frontend/src/components/custom-report/report-results.tsx`
- `frontend/src/components/custom-report/report-summary.tsx`
- `frontend/src/components/products/pareto-chart.tsx`
- `frontend/src/components/goals/goals-overview.tsx`
- `frontend/src/components/shared/ranking-table.tsx`
- `frontend/src/components/shared/ranking-table-linked.tsx`
- `frontend/src/components/shared/data-freshness.tsx`
- `frontend/src/components/sites/radar-comparison.tsx`
- `frontend/src/components/sites/site-detail-view.tsx`
- `frontend/src/components/staff/gamified-leaderboard.tsx`
- `frontend/src/components/alerts/alerts-overview.tsx`
- `frontend/src/app/(app)/dashboard/report/page.tsx`
- `frontend/src/app/(app)/reports/page.tsx`

### Findings

#### 🔴 [FE-1] Health dashboard division by zero when `dist.total === 0`
- **File:** `frontend/src/components/customers/health-dashboard.tsx:41`
- **Severity:** Critical
- **Category:** Division by zero
- **Current code:**
  ```typescript
  style={{ width: `${(b.count / dist.total) * 100}%` }}
  ```
- **Why it's wrong:** If all health bands are empty (no customers), `dist.total` = 0 → division produces `Infinity` → `width: "Infinity%"` → layout breaks.
- **Suggested fix:**
  ```typescript
  style={{ width: `${dist.total > 0 ? (b.count / dist.total) * 100 : 0}%` }}
  ```
- **Test to add:** Vitest: render `HealthDashboard` with empty distribution, assert no NaN/Infinity in DOM.

#### 🟡 [FE-2] Calendar heatmap ratio not clamped — opacity can exceed [0, 1]
- **File:** `frontend/src/components/dashboard/calendar-heatmap.tsx:8-14`
- **Severity:** Warning
- **Category:** Unclamped ratio
- **Current code:**
  ```typescript
  if (max === min) return isDark ? "var(--divider)" : "var(--divider)";
  const ratio = (value - min) / (max - min);
  const opacity = 0.2 + ratio * 0.8;
  ```
- **Why it matters:** If `value` falls outside `[min, max]` (possible with data updates after min/max computed), `ratio` can be > 1 or < 0, causing opacity outside [0.2, 1.0]. CSS `rgba` clamps automatically, but values like `opacity: 1.6` may behave differently across browsers.
- **Suggested fix:**
  ```typescript
  const ratio = Math.min(Math.max((value - min) / (max - min), 0), 1);
  ```

#### 🟡 [FE-3] Data freshness `getMinutesAgo()` can return negative for future timestamps
- **File:** `frontend/src/components/shared/data-freshness.tsx:11`
- **Severity:** Warning
- **Category:** Edge case
- **Current code:**
  ```typescript
  function getMinutesAgo(date: Date): number {
    return Math.floor((Date.now() - date.getTime()) / 60000);
  }
  ```
- **Why it matters:** If the server timestamp is ahead of the client clock, this produces negative values like "-5m ago". Unlikely in production but possible with clock drift.
- **Suggested fix:** `return Math.max(Math.floor((Date.now() - date.getTime()) / 60000), 0);`

#### 🟡 [FE-4] Site detail view ratio formatting inconsistency — mixed decimal places
- **File:** `frontend/src/components/sites/site-detail-view.tsx:44-46`
- **Severity:** Warning
- **Category:** Display inconsistency
- **Current code:**
  ```typescript
  { label: "Walk-in Ratio", value: `${(site.walk_in_ratio * 100).toFixed(1)}%` },
  { label: "Insurance Ratio", value: `${(site.insurance_ratio * 100).toFixed(1)}%` },
  { label: "Return Rate", value: `${(site.return_rate * 100).toFixed(2)}%` },
  ```
- **Why it matters:** Walk-in and Insurance use 1 decimal, Return Rate uses 2. Inconsistent display for similar percentage metrics on the same card.
- **Suggested fix:** Use `.toFixed(1)` for all three, or extract a `formatRatio()` helper.

#### 🟡 [FE-5] Custom report `formatCell` calls `.toLocaleString()` on `unknown` type
- **File:** `frontend/src/components/custom-report/report-results.tsx:55-70`
- **Severity:** Warning
- **Category:** Type safety
- **Current code:**
  ```typescript
  function formatCell(value: unknown, colName?: string): string {
    // ...
    return value.toLocaleString("en-EG", { maximumFractionDigits: 1 });
  }
  ```
- **Why it matters:** If `value` is an object, array, or undefined, `.toLocaleString()` may produce `"[object Object]"` or throw. Should add `typeof value === "number"` guard.
- **Suggested fix:**
  ```typescript
  if (typeof value !== "number") return String(value ?? "");
  ```

#### 🟡 [FE-6] `formatCompact()` uses inconsistent decimal places for M vs K
- **File:** `frontend/src/lib/formatters.ts:33-37`
- **Severity:** Warning
- **Category:** Display inconsistency
- **Current code:**
  ```typescript
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  ```
- **Why it matters:** Millions get 1 decimal (1.2M) but thousands get 0 (12K, not 12.3K). Minor cosmetic inconsistency.

#### 🟢 [FE-7] `comparison-kpi.tsx` no NaN guard on delta when both values are 0
- **File:** `frontend/src/components/comparison/comparison-kpi.tsx:15-17`
- **Severity:** Suggestion
- **Category:** Edge case
- **Current code:**
  ```typescript
  const delta = previousValue !== 0
    ? ((currentValue - previousValue) / previousValue) * 100
    : 0;
  ```
- **Why it matters:** Correctly handles division by zero (returns 0), but when both are 0, shows "0.0% ↑" which could be misleading. Consider showing "—" or "N/A" instead.

### Verified Correct (no issues)
- **Progress ring SVG math:** `target-progress.tsx` — circumference, offset, clamping to [0, 150] all correct
- **Return rate gauge:** Normalization and angle interpolation correct
- **Count-up animation:** Easing function `easeOutExpo`, progress clamping, interpolation all correct
- **Comparison period dates:** `use-comparison-trend.ts` — millisecond date math correct
- **Target progress:** Division-by-zero guard (`m.target > 0`), height clamped to 100%
- **Ranking table:** `Math.min(item.pct_of_total, 100)` correctly clamps bar width
- **Radar comparison:** `Math.max(..., 1)` in maxValues prevents division by zero
- **Staff leaderboard:** `Math.max(...items.map(i => i.value), 1)` — safe
- **RFM matrix:** `reduce` sum with 0 initial — correct
- **Report summary:** Empty array guard before average calculation
- **Goals overview:** Same progress ring math as target-progress — correct
- **Number formatters:** `formatCurrency`, `formatNumber` — proper locale, null handling

### Additional Findings (from deep agent audit)

#### 🔴 [FE-8] `formatPercent` misused for absolute percentages — adds unwanted "+" prefix
- **File:** Multiple:
  - `frontend/src/app/(app)/dashboard/report/page.tsx:100,118,137` — `formatPercent(item.pct_of_total)` shows "+15.2%" for "15.2% of total"
  - `frontend/src/components/dashboard/forecast-card.tsx:54` — `formatPercent(data.mape)` shows "+12.3%" for MAPE error magnitude
  - `frontend/src/components/dashboard/target-progress.tsx:143` — `formatPercent(ytdPct)` shows "+85.0%" for 85% achievement
  - `frontend/src/components/goals/goals-overview.tsx:33,90,240,314` — achievement percentages with "+"
- **Severity:** Critical
- **Category:** Semantic formatting error
- **Current code:**
  ```typescript
  // formatters.ts:19
  export function formatPercent(value: number) {
    return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
  }
  ```
- **Why it's wrong:** `formatPercent` is designed for growth deltas ("+5.2%", "-3.1%"). Using it for absolute percentages (market share, achievement, MAPE) adds a misleading "+" prefix. A 25% market share shows as "+25.0%". A MAPE of 12% shows as "+12.3%".
- **Suggested fix:** Create `formatAbsolutePercent`:
  ```typescript
  export function formatAbsolutePercent(value: number | null | undefined): string {
    if (value === null || value === undefined) return "N/A";
    return `${value.toFixed(1)}%`;
  }
  ```
- **Test to add:** Vitest: assert `formatAbsolutePercent(25)` returns `"25.0%"` not `"+25.0%"`.

#### 🔴 [FE-9] Double "++" prefix in forecast growing products
- **File:** `frontend/src/components/dashboard/forecast-card.tsx:93`
- **Severity:** Critical
- **Category:** Display bug
- **Current code:**
  ```typescript
  +{formatPercent(p.forecast_change_pct)}
  ```
- **Why it's wrong:** Template has literal `+`, then `formatPercent` adds another `+`. A 15% growth renders as `++15.0%`.
- **Suggested fix:** Remove the hardcoded `+`: `{formatPercent(p.forecast_change_pct)}`

#### 🟡 [FE-10] DayHero `Math.abs` + `formatPercent` contradicts arrow direction
- **File:** `frontend/src/components/dashboard/day-hero.tsx:38`
- **Severity:** Warning
- **Category:** Contradictory visual cues
- **Current code:**
  ```typescript
  {formatPercent(Math.abs(momGrowth))} vs last month
  ```
- **Why it matters:** `Math.abs` makes value positive, then `formatPercent` adds "+". A -15% decline shows as "+15.0% vs last month" with a red down arrow. The "+" contradicts the red/down visual.
- **Suggested fix:** `${Math.abs(momGrowth).toFixed(1)}% vs last month` — no sign since arrow shows direction.

#### 🟡 [FE-11] CSV download doesn't escape double quotes in cell values
- **File:** `frontend/src/components/custom-report/report-results.tsx:208-211`
- **Severity:** Warning
- **Category:** Data corruption
- **Current code:**
  ```typescript
  if (typeof cell === "string" && cell.includes(",")) return `"${cell}"`;
  ```
- **Why it matters:** If cell contains commas AND quotes (e.g., `Dr. Ahmed, "The Best"`), wrapping without escaping inner quotes produces malformed CSV.
- **Suggested fix:** `return \`"${cell.replace(/"/g, '""')}"\`;` and also wrap if cell contains quotes or newlines.

#### 🟡 [FE-12] NaN propagation in useCountUp when numericValue is NaN
- **File:** `frontend/src/hooks/use-count-up.ts:37-48` via `frontend/src/components/dashboard/kpi-card.tsx:46`
- **Severity:** Warning
- **Category:** Edge case
- **Why it matters:** `KPICard` checks `null`/`undefined` but not `NaN`. If API returns a non-parseable value, every animation frame renders "NaN" in the KPI card.
- **Suggested fix:** Add `Number.isNaN(numericValue)` guard.

#### 🟡 [FE-13] Inconsistent locale: `"ar-EG-u-nu-latn"` vs `"en-EG"` vs browser default
- **File:** `frontend/src/lib/formatters.ts` vs `frontend/src/components/custom-report/report-results.tsx:62` vs `frontend/src/app/(app)/reports/page.tsx:252`
- **Severity:** Warning
- **Category:** Inconsistent formatting
- **Why it matters:** Main formatters use `"ar-EG-u-nu-latn"`, report pages use `"en-EG"`, some components use no locale (browser default). The same number may format differently across pages.

---

## LAYER 6: Power BI DAX Measures & TMDL ✅

### Files Audited
- `powerbi/saas_demo.SemanticModel/definition/tables/_Measures.tmdl` (99 DAX measures)
- `powerbi/saas_demo.SemanticModel/definition/tables/fct_sales.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/dim_date.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/dim_customer.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/dim_product.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/dim_staff.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/dim_site.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/dim_billing.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/Time Intelligence.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/_ViewToggle.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/tables/_KPIDisplayMode.tmdl`
- `powerbi/saas_demo.SemanticModel/definition/relationships.tmdl`

### Findings

#### 🔴 [PBI-1] Financial columns use `dataType: double` — float for money
- **File:** `powerbi/saas_demo.SemanticModel/definition/tables/fct_sales.tmdl:66,74,83,92`
- **Severity:** Critical
- **Category:** Float for money
- **Current code:**
  ```
  column quantity
      dataType: double

  column sales
      dataType: double

  column discount
      dataType: double

  column net_amount
      dataType: double
  ```
- **Why it's wrong:** The PostgreSQL/dbt layer stores these as `NUMERIC(18,4)` / `ROUND(..., 2)` for exact decimal arithmetic. Power BI's `double` uses IEEE 754 which can produce artifacts like `1234.560000000001`. For financial reporting, this can cause rounding discrepancies: a SUM of 1M rows of doubles may differ from the dbt source by several EGP.
- **Suggested fix:** Change `dataType: double` to `dataType: decimal` for `sales`, `discount`, `net_amount`, and `quantity`. This maps to Power BI's `Decimal Number` (128-bit) which preserves precision.
- **Test to add:** Compare Power BI totals against dbt source for the same date range.

#### 🟡 [PBI-2] `Unique Customers` counts unknown customer key (-1) in DISTINCTCOUNT
- **File:** `powerbi/saas_demo.SemanticModel/definition/tables/_Measures.tmdl:52`
- **Severity:** Warning
- **Category:** Business logic
- **Current code:**
  ```dax
  measure 'Unique Customers' = DISTINCTCOUNT(fct_sales[customer_key])
  ```
- **Why it matters:** `customer_key = -1` represents "Unknown" customers. DISTINCTCOUNT includes this value, inflating the customer count by 1 for periods with any unknown transactions. Should exclude -1:
- **Suggested fix:**
  ```dax
  measure 'Unique Customers' =
      CALCULATE(
          DISTINCTCOUNT(fct_sales[customer_key]),
          fct_sales[customer_key] <> -1
      )
  ```

#### 🟡 [PBI-3] `Revenue vs PY Target %` hardcodes 10% growth target
- **File:** `powerbi/saas_demo.SemanticModel/definition/tables/_Measures.tmdl:769-774`
- **Severity:** Warning
- **Category:** Hardcoded magic number
- **Current code:**
  ```dax
  measure 'Revenue vs PY Target %' =
      VAR _py = CALCULATE([Net Revenue], SAMEPERIODLASTYEAR(dim_date[full_date]))
      VAR _target = _py * 1.1
      RETURN DIVIDE(_current, _target, 0)
  ```
- **Why it matters:** The `1.1` (10% growth target) is hardcoded. Different periods, categories, or sites may have different targets. The platform already has a `sales_targets` table for custom targets.
- **Suggested fix:** Either reference a targets table/parameter or document this as a fixed 10% benchmark.

#### 🟡 [PBI-4] Growth measures use `ABS(_prev)` in denominator — masks sign of base period
- **File:** `powerbi/saas_demo.SemanticModel/definition/tables/_Measures.tmdl:564,574,596,606,616`
- **Severity:** Warning
- **Category:** Business logic edge case
- **Current code:**
  ```dax
  measure 'Revenue MoM %' =
      VAR _current = [Net Revenue]
      VAR _prev = CALCULATE([Net Revenue], PREVIOUSMONTH(dim_date[full_date]))
      RETURN DIVIDE(_current - _prev, ABS(_prev), BLANK())
  ```
- **Why it matters:** Using `ABS(_prev)` means if previous month was -100 (net loss) and current is +50, growth = (50 - (-100)) / 100 = +150%. Without ABS, it would be (50 - (-100)) / (-100) = -150%. Both are debatable — `ABS` makes percentage direction always match the change direction, which is arguably more intuitive. This is a design choice but should be documented.

#### 🟢 [PBI-5] Revenue mix percentage measures use REMOVEFILTERS correctly
- **File:** `powerbi/saas_demo.SemanticModel/definition/tables/_Measures.tmdl:163,173,183,203,213`
- **Severity:** Suggestion (positive finding)
- **Details:** All revenue percentage measures (Cash %, Credit %, Delivery %, Insurance %, Walk-in %) correctly use `REMOVEFILTERS(dim_billing)` or `REMOVEFILTERS(fct_sales[is_walk_in])` for the "all" denominator. No `ALL()` vs `REMOVEFILTERS()` confusion. **Well done.**

#### 🟢 [PBI-6] Direction measures could use SIGN() instead of nested IF
- **File:** `powerbi/saas_demo.SemanticModel/definition/tables/_Measures.tmdl:622-674`
- **Severity:** Suggestion
- **Category:** Code simplification
- **Current code:**
  ```dax
  IF(ISBLANK(_p), 0, IF(_c > _p, 1, IF(_c < _p, -1, 0)))
  ```
- **Suggested fix:**
  ```dax
  IF(ISBLANK(_p), 0, SIGN(_c - _p))
  ```

### Verified Correct (no issues)
- **All `DIVIDE()` calls** use proper alternate result (0 or BLANK)
- **Time intelligence:** `DATESMTD`, `DATESYTD`, `SAMEPERIODLASTYEAR`, `PREVIOUSMONTH` all reference `dim_date[full_date]` — correct date table
- **Return measures:** Properly filter `fct_sales[is_return]`, use `ABS()` for absolute values
- **Pareto (Top 20%):** `ROUNDUP(COUNTROWS * 0.2, 0)` with `TOPN` + `SUMX` — correct approach
- **Staff/Product contribution:** `HASONEVALUE` guard prevents aggregation context errors
- **RANKX measures:** Use `ALL()` correctly to rank across all items
- **Data quality measures:** Correctly check for -1 keys, negative non-return quantities, orphan rows
- **Relationships:** All 6 relationships are fact-to-dim, many-to-one, correct cardinality
- **Conditional formatting colors:** Proper threshold cascading in `SWITCH(TRUE(), ...)`
- **Display folders:** Well-organized: Core KPIs, Revenue Mix, Returns, Customer/Product/Staff Analytics, Time Intelligence, Conditional Formatting, Data Quality, Report Helpers

---

## Top 10 Issues to Fix First

| Priority | ID | Title | Effort | Impact |
|----------|----|-------|--------|--------|
| 1 | DBT-7 | `metrics_summary` incremental corrupts MTD/YTD totals | Small (fix WHERE clause) | **All dashboard MTD/YTD KPIs wrong after incremental runs** |
| 2 | DBT-9/10/11 | 3 agg models missing `total_net_amount` column | Small (add column) | dbt tests fail, net revenue queries error |
| 3 | PY-1 | `daily_transactions` inconsistency across 3 code paths | Small (1 line fix) | KPI dashboard shows wrong transaction count |
| 4 | PY-2 | Return rate unit mismatch (0-1 vs 0-100) | Small (standardize in 2 files) | Frontend displays 0.03% instead of 3.42% |
| 5 | DBT-12 | `fct_sales` 32-bit hash has ~149 collisions at 1.13M rows | Medium (widen to BIGINT) | Silent row duplication/loss in JOINs |
| 6 | DBT-8 | `dim_date.year_week` wrong at year boundaries | Small (YEAR→ISOYEAR) | Weekly reports misgroup Dec/Jan boundary rows |
| 7 | PY-3 | Average return rate uses simple avg, not weighted | Small (change formula) | 69% overstatement of return rate |
| 8 | PBI-1 | Power BI financial columns use `double` not `decimal` | Medium (change dataType) | Floating-point artifacts in financial reports |
| 9 | FE-8 | `formatPercent` misused for absolute percentages | Small (add utility) | "+25.0%" shown for market share values |
| 10 | PQ-1 | IQR anomaly detection uses naive quartile indexing | Small (use `statistics.quantiles`) | Missed anomalies or false positives for small N |

---

## Files with No Issues Found

### Python
- `src/datapulse/analytics/models.py` — Pydantic models, well-typed with JsonDecimal
- `src/datapulse/analytics/service.py` — caching wrapper, no calculations
- `src/datapulse/analytics/customer_health.py` — delegates to SQL
- `src/datapulse/analytics/hierarchy_repository.py` — clean hierarchy queries
- `src/datapulse/analytics/search_repository.py` — text search, no math
- `src/datapulse/analytics/diagnostics.py` — diagnostic queries, no math
- `src/datapulse/explore/sql_builder.py` — well-secured SQL builder with whitelist
- `src/datapulse/reports/template_engine.py` — template rendering, no math
- `src/datapulse/bronze/loader.py` — correct batch progress calculation
- `src/datapulse/targets/repository.py` — clean Decimal arithmetic, division guards
- `src/datapulse/analytics/comparison_repository.py` — correct growth edge cases
- `src/datapulse/billing/plans.py` — clean plan definitions

### dbt SQL
- `dbt/models/staging/stg_sales.sql` — correct net_amount formula, proper COALESCE
- `dbt/models/bronze/bronze_sales.sql` — simple source reference
- `dbt/models/marts/dims/dim_customer.sql` — correct MD5 key with tenant_id
- `dbt/models/marts/dims/dim_product.sql` — correct MD5 key
- `dbt/models/marts/dims/dim_staff.sql` — correct MD5 key
- `dbt/models/marts/dims/dim_site.sql` — correct MD5 key
- `dbt/models/marts/dims/dim_billing.sql` — clean ROW_NUMBER key
- `dbt/models/marts/aggs/agg_sales_by_customer.sql` — correct GROUP BY
- `dbt/models/marts/aggs/agg_sales_by_product.sql` — correct COALESCE for returns
- `dbt/models/marts/features/feat_customer_segments.sql` — correct RFM NTILE
- `dbt/models/marts/features/feat_revenue_daily_rolling.sql` — correct windows
- `dbt/models/marts/features/feat_revenue_site_rolling.sql` — correct ratios
- `dbt/models/marts/features/feat_seasonality_daily.sql` — correct indices
- `dbt/models/marts/features/feat_seasonality_monthly.sql` — correct indices
- `dbt/models/marts/features/feat_product_lifecycle.sql` — correct dormant logic
- `dbt/macros/governorate_map.sql` — static lookup, no calculations
- `dbt/tests/assert_unknown_dimension_below_threshold.sql` — correct test

### Frontend
- `frontend/src/lib/formatters.ts` — proper locale, null handling (except FE-6)
- `frontend/src/hooks/use-count-up.ts` — correct easing, interpolation, clamping
- `frontend/src/hooks/use-comparison-trend.ts` — correct date math
- `frontend/src/components/dashboard/target-progress.tsx` — correct SVG, guards
- `frontend/src/components/dashboard/day-hero.tsx` — correct display logic
- `frontend/src/components/products/pareto-chart.tsx` — correct ABC display
- `frontend/src/components/goals/goals-overview.tsx` — correct progress ring
- `frontend/src/components/shared/ranking-table.tsx` — correct clamping
- `frontend/src/components/shared/ranking-table-linked.tsx` — correct clamping
- `frontend/src/components/staff/gamified-leaderboard.tsx` — correct max guard
- `frontend/src/components/customers/rfm-matrix.tsx` — correct reduce sum

### Power BI
- All 99 DAX measures use `DIVIDE()` with proper alternate results
- All relationships are correct cardinality (many-to-one, fact→dim)
- All time intelligence references `dim_date[full_date]` correctly
- All REMOVEFILTERS / ALL usage is correct for percentage-of-total calculations

### Config & Infrastructure
- `frontend/src/lib/constants.ts` — chart colors, nav items, no calculations
- `src/datapulse/pipeline/quality.py` — well-designed quality gates

---

_End of audit report. Generated 2026-04-07._
