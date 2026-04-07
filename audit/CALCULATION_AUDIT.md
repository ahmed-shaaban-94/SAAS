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
