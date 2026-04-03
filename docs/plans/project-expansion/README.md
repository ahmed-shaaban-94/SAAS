# DataPulse — Project Expansion Master Plan

> **Status**: PLANNED
> **Created**: 2026-04-03
> **Scope**: Phases 5–10 — Transform DataPulse from a single-tenant analytics tool into a full-featured, multi-tenant SaaS platform.

---

## Current State

DataPulse has completed **Phases 1–4**:

| Phase | Title | Status |
|-------|-------|--------|
| 1.x | Data Pipeline + Dashboard | DONE |
| 2.x | Automation & AI-Light | DONE |
| 3.x | ~~LangGraph AI~~ | CANCELLED (replaced by 2.8) |
| 4.x | Public Website | DONE |
| — | Android App | IN PROGRESS |
| — | The Great Fix | DONE |
| — | Enhancement 2 (Full Stack Flex) | DONE |

**What we have**: Medallion pipeline, 10+ analytics endpoints, Next.js dashboard, n8n automation, quality gates, Keycloak auth, RLS, Slack notifications, AI insights, public website, Android skeleton.

**What we need**: Multi-tenancy, billing, more data sources, self-service analytics, deeper AI, collaboration, and production-grade infrastructure.

---

## Expansion Roadmap

```
Phase 5          Phase 6          Phase 7          Phase 8          Phase 9          Phase 10
Multi-tenancy    Data Sources     Self-Service     AI & Intel       Collaboration    Scale
& Billing        & Connectors     Analytics        ligence          & Teams          & Infra
                                                                    
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Tenant   │    │ Google   │    │ Dashboard│    │ NL Query │    │ Comments │    │ K8s      │
│ Onboard  │───>│ Sheets   │───>│ Builder  │───>│ Engine   │───>│ System   │───>│ Deploy   │
│          │    │          │    │          │    │          │    │          │    │          │
│ Billing  │    │ DB Conn  │    │ Custom   │    │ Forecast │    │ Sharing  │    │ CDN      │
│ Stripe   │    │ MySQL/   │    │ Reports  │    │ Prophet/ │    │ Public   │    │ S3/MinIO │
│          │    │ MSSQL    │    │          │    │ ARIMA    │    │ Links    │    │          │
│ Usage    │    │          │    │ Export   │    │          │    │          │    │ Queue    │
│ Metering │    │ API Conn │    │ PDF/CSV  │    │ Smart    │    │ Teams &  │    │ Celery   │
│          │    │ Shopify/ │    │          │    │ Alerts   │    │ Roles    │    │          │
│ Admin    │    │ WooComm  │    │ Alerts   │    │          │    │          │    │ Monitor  │
│ Panel    │    │          │    │ Threshld │    │ Summaries│    │ Activity │    │ Grafana  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     |                |               |               |               |               |
  CRITICAL         HIGH           MEDIUM          MEDIUM           NICE           SCALE
  بدونها مفيش     أكبر قيمة      بيفرقنا عن     competitive     retention      لما الـ
  SaaS حقيقي     مضافة للعميل    أي dashboard    advantage       & stickiness   users يكتروا
```

---

## Phase Index

| Phase | Title | Priority | Plan | Dependencies |
|-------|-------|----------|------|-------------|
| [5](./phase-5-multi-tenancy.md) | Multi-tenancy & Billing | CRITICAL | Tenant onboarding, Stripe, usage metering, admin panel | None |
| [6](./phase-6-data-sources.md) | Data Sources & Connectors | HIGH | Google Sheets, DB connectors, API connectors, schema mapping | Phase 5 |
| [7](./phase-7-self-service.md) | Self-Service Analytics | MEDIUM | Dashboard builder, custom reports, exports, alerts | Phase 5 |
| [8](./phase-8-ai-intelligence.md) | AI & Intelligence | MEDIUM | NL queries, forecasting, smart alerts, Arabic summaries | Phase 5, builds on 2.8 |
| [9](./phase-9-collaboration.md) | Collaboration & Teams | NICE-TO-HAVE | Comments, sharing, team workspaces, activity feed | Phase 5, 7 |
| [10](./phase-10-scale-infra.md) | Scale & Infrastructure | WHEN NEEDED | K8s, S3, Celery, CDN, monitoring | Phase 5 |

---

## Dependency Graph

```
Phase 5 (Multi-tenancy) ─── MUST BE FIRST ───┐
     │                                         │
     ├──> Phase 6 (Data Sources)               │
     │         │                               │
     ├──> Phase 7 (Self-Service) ──────> Phase 9 (Collaboration)
     │         │                               │
     ├──> Phase 8 (AI & Intelligence)          │
     │                                         │
     └──> Phase 10 (Scale & Infra) ────────────┘
```

**Phase 5 is the foundation** — every other phase depends on proper multi-tenancy.

Phases 6, 7, 8 can run **in parallel** after Phase 5 is done.

Phase 9 needs Phase 7 (can't share dashboards that don't exist yet).

Phase 10 is triggered by **growth needs**, not a fixed timeline.

---

## Estimated Scope

| Phase | New Files (est.) | New Tests (est.) | New Endpoints | New UI Pages |
|-------|-----------------|-------------------|---------------|-------------|
| 5 | ~30 | ~120 | ~15 | 3–4 |
| 6 | ~25 | ~80 | ~10 | 2–3 |
| 7 | ~35 | ~90 | ~12 | 4–5 |
| 8 | ~20 | ~60 | ~8 | 2–3 |
| 9 | ~20 | ~50 | ~10 | 2–3 |
| 10 | ~15 (mostly config) | ~30 | ~3 | 1 |

---

## Tech Stack Additions

| Phase | New Technology | Purpose |
|-------|--------------|---------|
| 5 | Stripe SDK, stripe-webhooks | Billing & subscriptions |
| 5 | Redis (expand usage) | Rate limiting, session cache |
| 6 | Google Sheets API, SQLAlchemy multi-bind | External data sources |
| 7 | React DnD / dnd-kit | Drag-and-drop dashboard builder |
| 7 | Puppeteer/Playwright | Server-side PDF generation |
| 8 | Prophet / statsforecast | Time series forecasting |
| 8 | LangChain (light) or direct LLM API | Natural language queries |
| 9 | WebSocket (FastAPI) | Real-time collaboration |
| 10 | Kubernetes, Helm | Container orchestration |
| 10 | MinIO (S3-compatible) | Object storage |
| 10 | Prometheus + Grafana | Monitoring & alerting |
| 10 | Celery + Redis | Background job queue |

---

## Revenue Model Alignment

```
                    Free              Starter           Pro              Enterprise
                    ─────             ───────           ───               ──────────
Phase 5 Tenancy     ✓ 1 user          ✓ 5 users        ✓ 25 users       ✓ Unlimited
Phase 5 Data        1K rows           100K rows         1M rows          Unlimited
Phase 6 Sources     CSV/Excel only    + Google Sheets   + DB connectors  + Custom API
Phase 7 Dashboards  1 dashboard       5 dashboards      Unlimited        Unlimited
Phase 7 Exports     —                 CSV only          CSV + PDF        CSV + PDF + API
Phase 8 AI          —                 Basic insights    Full AI suite    Custom models
Phase 9 Collab      —                 —                 Sharing          Full teams
Phase 10 SLA        —                 —                 99.5%            99.9% + support
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Stripe integration complexity | HIGH | Start with simple checkout, iterate |
| Multi-tenant data isolation bugs | CRITICAL | Extensive RLS testing, pen-test before launch |
| External API rate limits (Google, etc.) | MEDIUM | Queue + retry + caching |
| Dashboard builder UX complexity | MEDIUM | Start with templates, not free-form |
| AI cost overruns | MEDIUM | Token budgets per tenant, cache responses |
| K8s operational complexity | HIGH | Start with managed K8s (EKS/GKE), GitOps |

---

## Success Metrics

| Metric | Target | Phase |
|--------|--------|-------|
| Tenant onboarding time | < 2 minutes | 5 |
| Data source connection time | < 5 minutes | 6 |
| Dashboard creation time | < 10 minutes | 7 |
| AI query response time | < 5 seconds | 8 |
| Monthly recurring revenue | Track from day 1 | 5+ |
| Tenant retention (30-day) | > 80% | All |
| API uptime | 99.5%+ | 10 |
