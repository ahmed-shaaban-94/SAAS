# Calculation Audit Report

**Date:** 2026-04-07
**Files scanned:** 488 (135 Python, 35 dbt SQL/YAML, 280 Frontend TS/TSX, 15 Power BI TMDL, 23 Migrations)

## Summary

- 🔴 Critical: _in progress_
- 🟡 Warnings: _in progress_
- 🟢 Suggestions: _in progress_

> This report is compiled incrementally. Each layer is audited and pushed as completed.

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
