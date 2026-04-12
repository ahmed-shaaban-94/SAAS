# DataPulse — CodeQL Security Scan Notes

> **Tool**: GitHub CodeQL 2.25.1  
> **Date**: 2026-04-12  
> **Scope**: `src/datapulse/`, `tests/`, `frontend/src/` (worktrees excluded)  
> **Total findings**: 100 (75 Python · 25 JavaScript/TypeScript)  
> **Suites**: `python-security-and-quality` · `javascript-security-and-quality`

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Error | 5 |
| 🟡 Warning | 24 |
| 🔵 Recommendation | 71 |
| **Total** | **100** |

## Rules Triggered

| # | Rule ID | Language | Severity | Findings | CWE | Description |
|---|---------|----------|----------|----------|-----|-------------|
| 1 | `py/side-effect-in-assert` | Python | 🔴 Error | 2 | — | An assert statement has a side-effect |
| 2 | `py/sql-injection` | Python | 🔴 Error | 2 | CWE-089 | SQL query built from user-controlled sources |
| 3 | `py/missing-call-to-init` | Python | 🔴 Error | 1 | — | Missing call to superclass `__init__` during object initialization |
| 4 | `py/import-of-mutable-attribute` | Python | 🟡 Warning | 20 | — | Importing value of mutable attribute |
| 5 | `js/http-to-file-access` | JavaScript/TypeScript | 🟡 Warning | 1 | CWE-434, CWE-912 | Network data written to file |
| 6 | `js/polynomial-redos` | JavaScript/TypeScript | 🟡 Warning | 1 | CWE-1333, CWE-400, CWE-730 | Polynomial regular expression used on uncontrolled data |
| 7 | `py/comparison-of-identical-expressions` | Python | 🟡 Warning | 1 | CWE-570, CWE-571 | Comparison of identical values |
| 8 | `py/multiple-definition` | Python | 🟡 Warning | 1 | CWE-563 | Variable defined multiple times |
| 9 | `js/unused-local-variable` | JavaScript/TypeScript | 🔵 Recommendation | 23 | — | Unused variable, import, function or class |
| 10 | `py/unnecessary-lambda` | Python | 🔵 Recommendation | 16 | — | Unnecessary lambda |
| 11 | `py/unused-global-variable` | Python | 🔵 Recommendation | 13 | CWE-563 | Unused global variable |
| 12 | `py/import-and-import-from` | Python | 🔵 Recommendation | 7 | — | Module is imported with 'import' and 'import from' |
| 13 | `py/empty-except` | Python | 🔵 Recommendation | 3 | CWE-390 | Empty except |
| 14 | `py/ineffectual-statement` | Python | 🔵 Recommendation | 3 | CWE-561 | Statement has no effect |
| 15 | `py/unused-local-variable` | Python | 🔵 Recommendation | 3 | CWE-563 | Unused local variable |
| 16 | `py/cyclic-import` | Python | 🔵 Recommendation | 2 | — | Cyclic import |
| 17 | `py/unused-import` | Python | 🔵 Recommendation | 1 | — | Unused import |

---

## Detailed Findings

### 🔴 Error — 5 finding(s)

#### `py/side-effect-in-assert` — An assert statement has a side-effect (2 findings)

**Language**: Python  
**Description**: Side-effects in assert statements result in differences between normal and optimized behavior.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `tests/test_annotations.py` | 62 | This 'assert' statement contains an [expression](1) which may have side effects. |
| 2 | `tests/test_annotations.py` | 69 | This 'assert' statement contains an [expression](1) which may have side effects. |

#### `py/sql-injection` — SQL query built from user-controlled sources (2 findings)

**Language**: Python  
**CWE**: CWE-089  
**Security Severity**: 8.8  
**Description**: Building a SQL query from user-controlled sources is vulnerable to insertion of malicious SQL code by the user.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/api/routes/embed.py` | 132 | This SQL query depends on a [user-provided value](1). |
| 2 | `src/datapulse/api/routes/explore.py` | 95 | This SQL query depends on a [user-provided value](1). |

#### `py/missing-call-to-init` — Missing call to superclass `__init__` during object initialization (1 finding)

**Language**: Python  
**Description**: An omitted call to a superclass `__init__` method may lead to objects of this class not being fully initialized.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/analytics/repository.py` | 23 | This class does not call [KpiRepository.__init__](1) during initialization. ([AnalyticsRepository.__init__](2) may be missing a call to a base class __init__) This class does not call [RankingReposito |

### 🟡 Warning — 24 finding(s)

#### `py/import-of-mutable-attribute` — Importing value of mutable attribute (20 findings)

**Language**: Python  
**Description**: Importing the value of a mutable attribute directly means that changes in global state will not be observed locally.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `tests/test_ai_light_endpoints.py` | 12 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 2 | `tests/test_analytics_endpoints.py` | 26 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 3 | `tests/test_analytics_endpoints_more.py` | 21 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 4 | `tests/test_annotations_endpoints.py` | 9 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 5 | `tests/test_branding.py` | 12 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 6 | `tests/test_csp_headers.py` | 7 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 7 | `tests/test_dashboard_layouts.py` | 8 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 8 | `tests/test_gamification_endpoints.py` | 11 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 9 | `tests/test_notifications_endpoints.py` | 9 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 10 | `tests/test_onboarding_endpoints.py` | 11 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 11 | `tests/test_pipeline_execute_endpoints.py` | 11 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 12 | `tests/test_pipeline_trigger.py` | 11 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 13 | `tests/test_quality_endpoints.py` | 21 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 14 | `tests/test_queries_endpoints.py` | 10 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 15 | `tests/test_rate_limiting.py` | 6 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 16 | `tests/test_reseller.py` | 13 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 17 | `tests/test_reseller_authorization.py` | 32 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 18 | `tests/test_search_endpoints.py` | 10 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 19 | `tests/test_targets_endpoints.py` | 12 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |
| 20 | `tests/test_views_endpoints.py` | 11 | Importing the value of 'create_app' from [module datapulse.api.app](1) means that any change made to [datapulse.api.app.create_app](2) will be not be observed locally. |

#### `js/http-to-file-access` — Network data written to file (1 finding)

**Language**: JavaScript/TypeScript  
**CWE**: CWE-434 · CWE-912  
**Security Severity**: 6.3  
**Description**: Writing network data directly to the file system allows arbitrary file upload and might indicate a backdoor.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `frontend/src/app/api/waitlist/route.ts` | 35 | Write to file system depends on [Untrusted data](1). |

#### `js/polynomial-redos` — Polynomial regular expression used on uncontrolled data (1 finding)

**Language**: JavaScript/TypeScript  
**CWE**: CWE-1333 · CWE-400 · CWE-730  
**Security Severity**: 7.5  
**Description**: A regular expression that can require polynomial time to match may be vulnerable to denial-of-service attacks.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `frontend/src/app/api/waitlist/route.ts` | 58 | This [regular expression](1) that depends on [a user-provided value](2) may run slow on strings starting with '!@!.' and with many repetitions of '!.'. |

#### `py/comparison-of-identical-expressions` — Comparison of identical values (1 finding)

**Language**: Python  
**CWE**: CWE-570 · CWE-571  
**Description**: Comparison of identical values, the intent of which is unclear.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `tests/test_pagination.py` | 40 | Comparison of identical values; use cmath.isnan() if testing for not-a-number. |

#### `py/multiple-definition` — Variable defined multiple times (1 finding)

**Language**: Python  
**CWE**: CWE-563  
**Description**: Assignment to a variable occurs multiple times without any intermediate use of that variable

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/onboarding/service.py` | 47 | This assignment to 'current_step' is unnecessary as it is [redefined](1) before this value is used. This assignment to 'current_step' is unnecessary as it is [redefined](2) before this value is used. |

### 🔵 Recommendation — 71 finding(s)

#### `js/unused-local-variable` — Unused variable, import, function or class (23 findings)

**Language**: JavaScript/TypeScript  
**Description**: Unused variables, imports, functions or classes may be a symptom of a bug and should be examined carefully.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `frontend/e2e/upload.spec.ts` | 2 | Unused import path. |
| 2 | `frontend/src/__tests__/components/accessibility.test.tsx` | 3 | Unused import userEvent. |
| 3 | `frontend/src/__tests__/components/error-boundary.test.tsx` | 42 | Unused variable rerender. |
| 4 | `frontend/src/__tests__/components/ranking-table.test.tsx` | 41 | Unused variable container. |
| 5 | `frontend/src/app/(app)/dashboard/page.tsx` | 4 | Unused imports BarChart3, Zap. |
| 6 | `frontend/src/app/(app)/sites/%5Bkey%5D/page.tsx` | 5 | Unused import MapPin. |
| 7 | `frontend/src/app/(app)/team/page.tsx` | 4 | Unused import ChevronDown. |
| 8 | `frontend/src/app/(app)/team/page.tsx` | 17 | Unused import useRoles. |
| 9 | `frontend/src/app/embed/%5Btoken%5D/page.tsx` | 25 | Unused variable setSelectedModel. |
| 10 | `frontend/src/components/branding/brand-settings.tsx` | 5 | Unused import postAPI. |
| 11 | `frontend/src/components/dashboard/billing-breakdown-chart.tsx` | 4 | Unused import Legend. |
| 12 | `frontend/src/components/dashboard/daily-trend-chart.tsx` | 4 | Unused import LabelList. |
| 13 | `frontend/src/components/dashboard/monthly-trend-chart.tsx` | 4 | Unused import BarChart. |
| 14 | `frontend/src/components/dashboard/trend-kpi-cards.tsx` | 7 | Unused imports formatNumber, formatPercent. |
| 15 | `frontend/src/components/gamification/gamification-dashboard.tsx` | 60 | Unused variable loadingEarned. |
| 16 | `frontend/src/components/goals/goals-overview.tsx` | 6 | Unused import formatPercent. |
| 17 | `frontend/src/components/layout/saved-views-menu.tsx` | 4 | Unused import Link. |
| 18 | `frontend/src/components/layout/sidebar.tsx` | 333 | Unused variable mainMargin. |
| 19 | `frontend/src/components/lineage/lineage-overview.tsx` | 8 | Unused import ArrowRight. |
| 20 | `frontend/src/components/products/product-hierarchy.tsx` | 10 | Unused import cn. |
| 21 | `frontend/src/components/returns/returns-overview.tsx` | 34 | Unused variable otherAmount. |
| 22 | `frontend/src/hooks/use-gamification.ts` | 3 | Unused import postAPI. |
| 23 | `powerbi/guide.html` | 718 | Unused variable sectionHeight. |

#### `py/unnecessary-lambda` — Unnecessary lambda (16 findings)

**Language**: Python  
**Description**: A lambda is used that calls through to a function without modifying any parameters

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `tests/test_ai_light.py` | 365 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 2 | `tests/test_branding.py` | 67 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 3 | `tests/test_bronze_validator.py` | 62 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 4 | `tests/test_bronze_validator.py` | 77 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 5 | `tests/test_bronze_validator.py` | 122 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 6 | `tests/test_bronze_validator.py` | 137 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 7 | `tests/test_config.py` | 140 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 8 | `tests/test_gamification_endpoints.py` | 49 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 9 | `tests/test_pipeline_execute_endpoints.py` | 36 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 10 | `tests/test_pipeline_trigger.py` | 56 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 11 | `tests/test_quality_endpoints.py` | 109 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 12 | `tests/test_quality_endpoints.py` | 110 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 13 | `tests/test_quality_endpoints.py` | 111 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 14 | `tests/test_reseller.py` | 58 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 15 | `tests/test_reseller_authorization.py` | 96 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |
| 16 | `tests/test_targets_endpoints.py` | 46 | This 'lambda' is just a simple wrapper around a callable object. Use that object directly. |

#### `py/unused-global-variable` — Unused global variable (13 findings)

**Language**: Python  
**CWE**: CWE-563  
**Description**: Global variable is defined but not used

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/analytics/customer_health.py` | 18 | The global variable '_ZERO' is not used. |
| 2 | `src/datapulse/anomalies/detector.py` | 14 | The global variable '_ZERO' is not used. |
| 3 | `src/datapulse/api/jwt.py` | 50 | The global variable '_jwks_cache_time' is not used. |
| 4 | `src/datapulse/branding/repository.py` | 20 | The global variable '_DEFAULT_BRANDING' is not used. |
| 5 | `src/datapulse/cache.py` | 35 | The global variable '_redis_mod' is not used. |
| 6 | `src/datapulse/cache.py` | 110 | The global variable '_last_attempt' is not used. |
| 7 | `src/datapulse/cache.py` | 134 | The global variable '_CACHE_MISS' is not used. |
| 8 | `src/datapulse/explore/manifest_parser.py` | 222 | The global variable '_catalog_built_at' is not used. |
| 9 | `src/datapulse/graph/analyzers/dbt_analyzer.py` | 21 | The global variable '_COL_REF_RE' is not used. |
| 10 | `src/datapulse/graph/analyzers/typescript_analyzer.py` | 26 | The global variable '_HOOK_CALL_RE' is not used. |
| 11 | `src/datapulse/pipeline/quality_repository.py` | 24 | The global variable '_COLUMNS' is not used. |
| 12 | `src/datapulse/reports/template_engine.py` | 29 | The global variable '_PARAM_PATTERN' is not used. |
| 13 | `tests/test_upload_service.py` | 15 | The global variable '_XLS_MAGIC' is not used. |

#### `py/import-and-import-from` — Module is imported with 'import' and 'import from' (7 findings)

**Language**: Python  
**Description**: A module is imported with the "import" and "import from" statements

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `tests/conftest.py` | 41 | Module 'datapulse.api.app' is imported with both 'import' and 'import from'. |
| 2 | `tests/test_bronze_main.py` | 13 | Module 'datapulse.bronze.__main__' is imported with both 'import' and 'import from'. |
| 3 | `tests/test_cache.py` | 10 | Module 'datapulse.cache' is imported with both 'import' and 'import from'. |
| 4 | `tests/test_jwt.py` | 77 | Module 'datapulse.api.jwt' is imported with both 'import' and 'import from'. |
| 5 | `tests/test_jwt.py` | 152 | Module 'datapulse.api.jwt' is imported with both 'import' and 'import from'. |
| 6 | `tests/test_security_hardening.py` | 284 | Module 'datapulse.api.app' is imported with both 'import' and 'import from'. |
| 7 | `tests/test_watcher_main.py` | 10 | Module 'datapulse.watcher.__main__' is imported with both 'import' and 'import from'. |

#### `py/empty-except` — Empty except (3 findings)

**Language**: Python  
**CWE**: CWE-390  
**Description**: Except doesn't do anything and has no comment

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/bronze/__main__.py` | 8 | 'except' clause does nothing but pass and there is no explanatory comment. |
| 2 | `src/datapulse/scheduler.py` | 319 | 'except' clause does nothing but pass and there is no explanatory comment. |
| 3 | `tests/test_export.py` | 67 | 'except' clause does nothing but pass and there is no explanatory comment. |

#### `py/ineffectual-statement` — Statement has no effect (3 findings)

**Language**: Python  
**CWE**: CWE-561  
**Description**: A statement has no effect

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/metrics.py` | 63 | This statement has no effect. |
| 2 | `src/datapulse/metrics.py` | 64 | This statement has no effect. |
| 3 | `src/datapulse/metrics.py` | 65 | This statement has no effect. |

#### `py/unused-local-variable` — Unused local variable (3 findings)

**Language**: Python  
**CWE**: CWE-563  
**Description**: Local variable is defined but not used

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/analytics/service.py` | 219 | Variable target_date is not used. |
| 2 | `tests/test_anomaly_detector.py` | 98 | Variable _result is not used. |
| 3 | `tests/test_forecasting_repository.py` | 283 | Variable mock_execute is not used. |

#### `py/cyclic-import` — Cyclic import (2 findings)

**Language**: Python  
**Description**: Module forms part of an import cycle, thereby indirectly importing itself.

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/api/routes/health.py` | 236 | Import of module [datapulse.scheduler](1) begins an import cycle. |
| 2 | `src/datapulse/scheduler.py` | 333 | Import of module [datapulse.api.routes.health](1) begins an import cycle. |

#### `py/unused-import` — Unused import (1 finding)

**Language**: Python  
**Description**: Import is not required as it is not used

| # | File | Line | Message |
|---|------|------|---------|
| 1 | `src/datapulse/api/deps.py` | 38 | Import of 'get_engine' is not used. |
