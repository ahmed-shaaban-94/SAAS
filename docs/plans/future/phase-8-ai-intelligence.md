# Phase 8 — AI & Intelligence

> **Status**: PLANNED
> **Priority**: MEDIUM
> **Dependencies**: Phase 5 (Multi-tenancy), builds on Phase 2.8 (AI-Light)
> **Goal**: Upgrade AI from basic anomaly detection to natural language queries, forecasting, smart alerts, and Arabic/English bilingual summaries.

---

## What We Have (Phase 2.8)

- OpenRouter integration for LLM-generated change narratives
- Statistical anomaly detection (z-score based)
- `/insights` page with AI summaries

## What We're Adding

- Natural language queries ("إيه أعلى 5 منتجات مبيعاً الشهر ده؟")
- Time series forecasting (predict next month/quarter sales)
- Smart alerts that learn what's "normal" for each tenant
- AI-powered data quality suggestions

---

## Visual Overview

```
Phase 8 — AI & Intelligence
═══════════════════════════════════════════════════════════════

  8.1 NL Query Engine        Arabic + English → SQL → Chart
       │
       v
  8.2 Forecasting            Prophet/statsforecast, confidence intervals
       │
       v
  8.3 Smart Alerts           ML-based anomaly detection per tenant
       │
       v
  8.4 AI Summaries v2        Bilingual, actionable, context-aware

═══════════════════════════════════════════════════════════════
```

---

## Sub-Phases

### 8.1 Natural Language Query Engine

**Goal**: Users ask questions in Arabic or English, get charts and tables back.

**Architecture**:
```
User Question (Arabic/English)
        │
        v
  ┌─────────────┐
  │ LLM (Claude │     Context: table schemas, sample data,
  │  or GPT-4)  │ <── previous queries, tenant's data profile
  └──────┬──────┘
         │
         v
  ┌─────────────┐
  │ SQL Query   │     Parameterized, read-only, tenant-scoped
  │ (validated) │
  └──────┬──────┘
         │
         v
  ┌─────────────┐
  │ Execute on  │     Run against gold layer (marts schema)
  │ PostgreSQL  │
  └──────┬──────┘
         │
         v
  ┌─────────────┐
  │ Auto-chart  │     Detect best visualization for result shape
  │ + Answer    │
  └─────────────┘
```

**Implementation**:
- `src/datapulse/ai/` module:
  - `nl_query.py` — Question → SQL pipeline:
    1. Schema context builder (table/column descriptions)
    2. LLM prompt with few-shot examples (Arabic + English)
    3. SQL validation (whitelist tables, enforce tenant_id, read-only)
    4. Query execution with timeout
    5. Result formatting + chart type suggestion
  - `chart_suggest.py` — Heuristic chart type selection based on result shape
  - `query_cache.py` — Cache frequent queries (Redis, keyed by normalized question)
- API: `POST /api/v1/ai/query` — `{question: string}` → `{sql, data, chart_type, answer}`
- Frontend:
  - Chat-like query interface on `/insights` page
  - Query history with re-run capability
  - Auto-generated chart from results
  - "Explain this" button for the generated SQL

**Safety**:
- SQL injection: LLM output is parameterized and validated before execution
- Only SELECT allowed (no INSERT/UPDATE/DELETE)
- Query timeout: 10 seconds max
- Token budget per tenant per day
- Result row limit: 10,000 rows

**Tests**: ~20 tests (including adversarial SQL injection attempts)

---

### 8.2 Forecasting

**Goal**: Predict future sales, returns, and other metrics.

**Models**:
| Library | Use Case | Why |
|---------|----------|-----|
| `statsforecast` | Quick forecasts (AutoARIMA, ETS) | Fast, no heavy deps |
| `prophet` | Seasonal decomposition, holidays | Best for business data |

**Implementation**:
- `src/datapulse/ai/forecasting.py`:
  - `forecast_metric(tenant_id, metric, periods, model)` → `ForecastResult`
  - Support daily, weekly, monthly granularity
  - Confidence intervals (80%, 95%)
  - Automatic model selection based on data characteristics
- `src/datapulse/ai/models.py` — `ForecastResult`, `ForecastPoint(date, value, lower, upper)`
- API:
  - `POST /api/v1/ai/forecast` — `{metric, periods, granularity}`
  - `GET /api/v1/ai/forecast/models` — Available models + suitability
- Frontend:
  - Forecast toggle on trend charts (extends line into future)
  - Shaded confidence interval bands
  - Model info tooltip

**Tests**: ~15 tests (with synthetic time series data)

---

### 8.3 Smart Alerts (ML-based)

**Goal**: Learn what's "normal" for each tenant and alert on deviations.

**Approach**:
- Build per-tenant baselines using historical data
- Use Isolation Forest or z-score with seasonal adjustment
- Account for day-of-week, month-of-year, holidays

**Implementation**:
- `src/datapulse/ai/smart_alerts.py`:
  - `build_baseline(tenant_id, metric, lookback_days)` — Train/update baseline
  - `check_anomaly(tenant_id, metric, current_value)` → `AnomalyResult`
  - Severity levels: info, warning, critical
- Integrate with Phase 7.5 alerts:
  - New alert type: `anomaly` (in addition to threshold/change)
  - Auto-create smart alert rules for key metrics on tenant onboarding
- n8n workflow: nightly baseline recalculation

**Tests**: ~10 tests

---

### 8.4 AI Summaries v2

**Goal**: Rich, bilingual, actionable daily/weekly summaries.

**Improvements over Phase 2.8**:
| Feature | 2.8 (Current) | 8.4 (New) |
|---------|---------------|-----------|
| Language | English only | Arabic + English |
| Scope | Daily changes | Daily + weekly + monthly |
| Context | Single metric | Cross-metric correlation |
| Actions | Descriptive only | Actionable recommendations |
| Delivery | Dashboard only | Dashboard + email + Slack |

**Implementation**:
- `src/datapulse/ai/summaries.py`:
  - `generate_summary(tenant_id, period, language)` → `AISummary`
  - Context injection: KPIs, trends, anomalies, forecasts, alerts
  - LLM prompt engineering for actionable Arabic business writing
- Templates:
  - Daily brief: "Today's top 3 insights + 1 action item"
  - Weekly digest: "Week performance vs. previous + trend analysis"
  - Monthly report: "Month review + next month forecast + recommendations"
- API: `GET /api/v1/ai/summary?period=daily&lang=ar`
- Frontend: Summary cards on dashboard with language toggle

**Tests**: ~15 tests

---

## New Python Modules

```
src/datapulse/ai/
├── __init__.py
├── nl_query.py          # Natural language → SQL → Result
├── chart_suggest.py     # Auto chart type selection
├── query_cache.py       # Redis query cache
├── forecasting.py       # Time series forecasting
├── smart_alerts.py      # ML-based anomaly detection
├── summaries.py         # Bilingual AI summaries v2
└── models.py            # AI-specific Pydantic models
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ai/query` | Natural language query |
| GET | `/api/v1/ai/query/history` | Query history |
| POST | `/api/v1/ai/forecast` | Generate forecast |
| GET | `/api/v1/ai/forecast/models` | Available forecast models |
| GET | `/api/v1/ai/summary` | AI summary for period |
| GET | `/api/v1/ai/anomalies` | Current anomalies |

---

## Cost Control

| Control | Implementation |
|---------|---------------|
| Token budget | Max tokens/day per tenant (stored in tenant settings) |
| Query cache | Cache identical questions for 1 hour |
| Model tiering | Free plan: small model, Pro: large model |
| Rate limit | 20 AI queries/hour for Starter, 100 for Pro |
| Fallback | If LLM unavailable, show statistical summary only |

---

## Acceptance Criteria

- [ ] NL query: "ايه اعلى منتج مبيعات" returns correct top product
- [ ] NL query: SQL injection attempts are blocked
- [ ] Forecast: monthly sales prediction with < 15% MAPE on test data
- [ ] Forecast: confidence intervals displayed on trend charts
- [ ] Smart alerts: detect simulated anomaly within 1 evaluation cycle
- [ ] Summaries: Arabic summary is fluent and actionable
- [ ] Token budgets enforced per tenant
- [ ] All features degrade gracefully when LLM is unavailable
- [ ] 60+ new tests, all passing
