# ADR-005: Analytics repository split into mixin classes

**Status**: Accepted  
**Date**: 2026-04-09  
**Deciders**: Analytics Engineer

## Context

`src/datapulse/analytics/repository.py` grew to 1125 lines as the analytics surface expanded. The file contained:
- KPI summary methods with complex CTEs (~700 lines)
- Daily/monthly trend queries
- Top-N ranking queries for product/customer/staff/site
- Return analysis and staff quota queries

All 20 methods shared a single class `AnalyticsRepository` with one `__init__(session)`. Each method used `self._session` and had no dependencies on other methods in the class. The only shared state was the SQLAlchemy session.

At 1125 lines, the file violated the project's 800-line maximum and made it difficult to navigate to a specific domain's methods.

## Decision

Split `repository.py` into four **mixin classes** (no `__init__`, assume `self._session` exists), composed by a thin `AnalyticsRepository` facade:

```
kpi_repository.py (785 lines)      → class KpiRepository
trend_repository.py (60 lines)     → class TrendRepository
ranking_repository.py (241 lines)  → class RankingRepository
returns_repository.py (96 lines)   → class ReturnsRepository

repository.py (30 lines)           → class AnalyticsRepository(KpiRepository,
                                                              TrendRepository,
                                                              RankingRepository,
                                                              ReturnsRepository)
```

Python's MRO (Method Resolution Order) makes all 20 methods available on `AnalyticsRepository`. The facade's `__init__` sets `self._session`, which all mixin methods use via the shared instance.

**The public interface is unchanged** — all callers import and use `AnalyticsRepository` identically.

## Consequences

**Good:**
- Each file has a single clear responsibility (KPI, trends, rankings, returns)
- Files are within the 800-line project limit
- New analytics methods go in the correct focused file
- `AnalyticsRepository` remains the single import point — zero changes to callers

**Risks/trade-offs:**
- Multiple inheritance can surprise engineers unfamiliar with Python's MRO
- Mixin classes without `__init__` cannot be instantiated standalone for unit testing (must use `AnalyticsRepository` or mock `_session`)
- Searching for a method requires knowing which mixin it lives in (mitigated by the facade's docstring listing all 4 mixins)
