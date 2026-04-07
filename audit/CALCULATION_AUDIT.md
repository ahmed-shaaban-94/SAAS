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
