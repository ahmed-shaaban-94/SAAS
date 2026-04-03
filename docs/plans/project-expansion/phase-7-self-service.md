# Phase 7 — Self-Service Analytics

> **Status**: PLANNED
> **Priority**: MEDIUM
> **Dependencies**: Phase 5 (Multi-tenancy)
> **Goal**: Let users build custom dashboards, create scheduled reports, export data, and set up automated alerts — without needing a developer.

---

## Why This Matters

The current dashboard is fixed — same pages, same charts for everyone. For a real SaaS:
- Different roles need different views (CEO vs. sales rep vs. warehouse manager)
- Users want to save and share their analyses
- Automated reports replace manual "pull the numbers" requests
- Alerts catch problems before they become crises

---

## Visual Overview

```
Phase 7 — Self-Service Analytics
═══════════════════════════════════════════════════════════════

  7.1 Saved Views & Bookmarks    Persist filter state per user
       │
       v
  7.2 Custom Dashboard Builder   Drag-and-drop widget layout
       │
       v
  7.3 Scheduled Reports          PDF/email on cron
       │
       v
  7.4 Data Export                 CSV, Excel, PDF from any view
       │
       v
  7.5 Alerts & Thresholds        "Notify me when X happens"

═══════════════════════════════════════════════════════════════
```

---

## Sub-Phases

### 7.1 Saved Views & Bookmarks

**Goal**: Users save their current filter state and return to it later.

**Implementation**:
- `src/datapulse/views/` module:
  - `models.py` — `SavedView(id, tenant_id, user_id, name, page, filters, is_default)`
  - `repository.py` — CRUD for `saved_views` table
- API: `GET/POST/DELETE /api/v1/views`
- Frontend:
  - "Save current view" button in filter bar
  - Saved views dropdown in sidebar
  - Set default view per page

**Database**:
```sql
CREATE TABLE public.saved_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    page VARCHAR(50) NOT NULL,      -- 'dashboard', 'products', etc.
    filters JSONB NOT NULL,          -- {date_from, date_to, site, ...}
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Tests**: ~15 tests

---

### 7.2 Custom Dashboard Builder

**Goal**: Drag-and-drop dashboard creation with configurable widgets.

**Widget Types**:
| Widget | Description | Config |
|--------|-------------|--------|
| KPI Card | Single metric with trend | metric, comparison_period |
| Line Chart | Time series | metrics[], date_range, granularity |
| Bar Chart | Category comparison | metric, group_by, top_n |
| Table | Ranked data table | columns[], sort_by, limit |
| Pie Chart | Distribution | metric, group_by |
| Stat Grid | Multiple KPIs in grid | metrics[] |

**Implementation**:
- `src/datapulse/dashboards/` module:
  - `models.py` — `Dashboard`, `Widget`, `WidgetConfig`
  - `repository.py` — CRUD for dashboards + widgets
  - `query_builder.py` — Build SQL from widget config (safe, parameterized)
- Frontend:
  - Grid layout with `react-grid-layout` or `dnd-kit`
  - Widget config panel (metric picker, date range, grouping)
  - Live preview while editing
  - Responsive layout (auto-reflow on mobile)
- Templates: 5 pre-built dashboard templates:
  1. Executive Summary
  2. Sales Team Performance
  3. Product Portfolio
  4. Customer Intelligence
  5. Returns & Quality

**Database**:
```sql
CREATE TABLE public.dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    layout JSONB NOT NULL DEFAULT '[]',  -- Widget positions + sizes
    is_template BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.dashboard_widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID NOT NULL REFERENCES public.dashboards(id) ON DELETE CASCADE,
    widget_type VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    config JSONB NOT NULL DEFAULT '{}',  -- metric, filters, groupBy, etc.
    position JSONB NOT NULL DEFAULT '{}' -- x, y, w, h
);
```

**Tests**: ~25 tests

---

### 7.3 Scheduled Reports

**Goal**: Automatically generate and email PDF reports on a schedule.

**Implementation**:
- `src/datapulse/reports/` module:
  - `models.py` — `ReportSchedule`, `ReportRun`
  - `generator.py` — Render dashboard to PDF (Playwright/Puppeteer server-side)
  - `scheduler.py` — n8n workflow creation for scheduled delivery
  - `email_sender.py` — SMTP/SendGrid email with PDF attachment
- API:
  - `POST /api/v1/reports/schedules` — Create schedule (dashboard_id, cron, recipients)
  - `GET /api/v1/reports/schedules` — List schedules
  - `POST /api/v1/reports/generate` — One-off generation
- Frontend:
  - "Schedule Report" button on each dashboard
  - Schedule config: frequency (daily/weekly/monthly), time, recipients
  - Report history with download links

**Tests**: ~15 tests

---

### 7.4 Data Export

**Goal**: Export any view's data as CSV, Excel, or PDF.

**Export Formats**:
| Format | Library | Use Case |
|--------|---------|----------|
| CSV | Built-in | Data analysis, import to other tools |
| Excel | openpyxl | Business users, formatted tables |
| PDF | Playwright render | Formal reports, sharing |

**Implementation**:
- `src/datapulse/export/` module:
  - `csv_exporter.py` — Polars DataFrame → CSV stream
  - `excel_exporter.py` — Polars → Excel with formatting
  - `pdf_exporter.py` — Server-side page render → PDF
- API: `GET /api/v1/export/{format}?page=...&filters=...`
- Frontend: Export button in header bar, format picker dropdown
- Streaming response for large exports (no memory blow-up)

**Tests**: ~15 tests

---

### 7.5 Alerts & Thresholds

**Goal**: "Notify me when sales drop below X" or "Alert when returns exceed Y%".

**Alert Types**:
| Type | Example | Check |
|------|---------|-------|
| Threshold | "Sales < 100K EGP/day" | Metric vs. static value |
| Change | "MoM growth drops > 20%" | Metric vs. previous period |
| Anomaly | "Unusual spike in returns" | Statistical deviation (builds on Phase 2.8) |

**Implementation**:
- `src/datapulse/alerts/` module:
  - `models.py` — `AlertRule`, `AlertEvent`, `AlertChannel`
  - `evaluator.py` — Check rules against current data
  - `service.py` — Evaluate all active rules on schedule
  - `channels.py` — Delivery: email, Slack, in-app notification
- n8n workflow: periodic alert evaluation (every 15 min or hourly)
- API:
  - `CRUD /api/v1/alerts/rules` — Manage alert rules
  - `GET /api/v1/alerts/history` — Past alert events
  - `PATCH /api/v1/alerts/rules/{id}/mute` — Mute/unmute
- Frontend:
  - Alert rules page: create/edit/delete rules
  - Alert bell icon in header with unread count
  - In-app notification panel (slide-out)

**Database**:
```sql
CREATE TABLE public.alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    condition VARCHAR(20) NOT NULL,    -- 'gt', 'lt', 'change_gt', 'change_lt'
    threshold NUMERIC(18,4) NOT NULL,
    channels JSONB DEFAULT '["in_app"]',
    is_active BOOLEAN DEFAULT true,
    muted_until TIMESTAMPTZ,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.alert_events (
    id BIGSERIAL PRIMARY KEY,
    rule_id UUID NOT NULL REFERENCES public.alert_rules(id),
    tenant_id UUID NOT NULL,
    metric_value NUMERIC(18,4),
    threshold_value NUMERIC(18,4),
    message TEXT,
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Tests**: ~20 tests

---

## Acceptance Criteria

- [ ] Users can save and restore filter views
- [ ] Dashboard builder: create dashboard with 4+ widget types via drag-and-drop
- [ ] Dashboard templates: 5 pre-built templates available on first use
- [ ] PDF report generation completes in < 30 seconds
- [ ] Scheduled reports deliver on time via email
- [ ] CSV/Excel export works for datasets up to 1M rows (streaming)
- [ ] Alerts trigger within 15 minutes of threshold breach
- [ ] In-app notifications appear in real-time
- [ ] All features respect tenant isolation and plan limits
- [ ] 90+ new tests, all passing
