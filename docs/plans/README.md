# DataPulse — Project Plans

> Comprehensive planning documentation organized by phase and topic.

---

## Navigation

```
docs/plans/
├── README.md                        ← You are here
│
├── phase-1-data-pipeline/           # Foundation → Bronze → Silver → Gold → Dashboard
│   ├── README.md                    # Phase 1 overview & index
│   ├── 1.1-foundation.md           # Docker, Python env, import pipeline
│   ├── 1.2-bronze-layer.md         # Excel → Polars → Parquet → PostgreSQL
│   ├── 1.3-silver-layer.md         # dbt staging: cleaning, dedup, normalization
│   ├── 1.4-gold-layer.md           # Star schema, aggregations, FastAPI API
│   ├── 1.5-dashboard.md            # Next.js 14, 6 pages, Recharts, E2E
│   └── 1.6-polish-and-testing.md   # Security audit, 95%+ coverage, error handling
│
├── phase-2-automation/              # Pipeline automation, quality gates, AI
│   ├── README.md                    # Phase 2 overview & index
│   ├── 2.0-infra-prep.md           # API volumes, deps, CORS
│   ├── 2.1-n8n-infrastructure.md   # n8n + Redis Docker services
│   ├── 2.2-pipeline-tracking.md    # pipeline_runs table, CRUD API, 53 tests
│   ├── 2.3-webhook-execution.md    # Executor, trigger API, n8n workflow
│   ├── 2.4-file-watcher.md         # watchdog directory monitor, auto-trigger
│   ├── 2.5-quality-gates.md        # 7 quality checks, quality_checks table, 79 tests
│   ├── 2.6-notifications.md        # Slack workflows (success/failure/digest/error)
│   ├── 2.7-pipeline-dashboard.md   # /pipeline page, 5 components, E2E
│   └── 2.8-ai-light.md             # OpenRouter, anomaly detection, /insights
│
├── phase-4-public-website/          # Marketing site & SEO
│   ├── README.md                    # Phase 4 overview & index
│   ├── 4.1-setup-and-hero.md       # Route groups, marketing layout, hero section
│   ├── 4.2-features-and-pipeline.md # Features grid, pipeline visualization
│   ├── 4.3-pricing-and-faq.md      # Stats, pricing tiers, FAQ, tech badges
│   ├── 4.4-auth-and-waitlist.md    # Waitlist form, legal pages, API route
│   ├── 4.5-seo-and-performance.md  # Meta tags, JSON-LD, sitemap, OG image
│   └── 4.6-polish-and-testing.md   # Accessibility, E2E tests, responsive QA
│
└── validation-and-debugging/        # Testing, quality, security, debugging
    ├── README.md                    # Overview & index
    ├── backend-testing.md           # pytest strategy, fixtures, coverage targets
    ├── frontend-testing.md          # Playwright E2E, component testing
    ├── dbt-testing.md               # Schema tests, data tests, source freshness
    ├── data-quality.md              # 7 quality checks, pipeline quality flow
    ├── security-audit.md            # OWASP, RLS, auth, CORS, headers
    ├── debugging-runbook.md         # Common issues, Docker/DB/API/frontend debugging
    └── performance-testing.md       # API benchmarks, DB optimization, Lighthouse
```

---

## Phase Overview

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|-----------------|
| **1.1** | [Foundation](./phase-1-data-pipeline/1.1-foundation.md) | :white_check_mark: Done | Docker, Python env, import pipeline |
| **1.2** | [Bronze Layer](./phase-1-data-pipeline/1.2-bronze-layer.md) | :white_check_mark: Done | 1.1M rows in PostgreSQL |
| **1.3** | [Silver Layer](./phase-1-data-pipeline/1.3-silver-layer.md) | :white_check_mark: Done | Cleaned data, 7 dbt tests |
| **1.4** | [Gold Layer](./phase-1-data-pipeline/1.4-gold-layer.md) | :white_check_mark: Done | Star schema, FastAPI API |
| **1.5** | [Dashboard](./phase-1-data-pipeline/1.5-dashboard.md) | :white_check_mark: Done | 6 pages, Recharts, E2E |
| **1.6** | [Polish & Testing](./phase-1-data-pipeline/1.6-polish-and-testing.md) | :white_check_mark: Done | 95%+ coverage, security audit |
| **2.0** | [Infra Prep](./phase-2-automation/2.0-infra-prep.md) | :white_check_mark: Done | API volumes, CORS |
| **2.1** | [n8n Infrastructure](./phase-2-automation/2.1-n8n-infrastructure.md) | :white_check_mark: Done | n8n + Redis |
| **2.2** | [Pipeline Tracking](./phase-2-automation/2.2-pipeline-tracking.md) | :white_check_mark: Done | 5 endpoints, 53 tests |
| **2.3** | [Webhook Execution](./phase-2-automation/2.3-webhook-execution.md) | :white_check_mark: Done | Executor, n8n workflow |
| **2.4** | [File Watcher](./phase-2-automation/2.4-file-watcher.md) | :white_check_mark: Done | watchdog auto-trigger |
| **2.5** | [Quality Gates](./phase-2-automation/2.5-quality-gates.md) | :white_check_mark: Done | 7 checks, 79 tests |
| **2.6** | [Notifications](./phase-2-automation/2.6-notifications.md) | :white_check_mark: Done | 4 Slack workflows |
| **2.7** | [Pipeline Dashboard](./phase-2-automation/2.7-pipeline-dashboard.md) | :white_check_mark: Done | /pipeline page, E2E |
| **2.8** | [AI-Light](./phase-2-automation/2.8-ai-light.md) | :white_check_mark: Done | OpenRouter insights |
| **4.1–4.6** | [Public Website](./phase-4-public-website/) | :white_check_mark: Done | Landing page, SEO, waitlist |

---

## Cross-Cutting Concerns

| Topic | Document | Scope |
|-------|----------|-------|
| Backend Testing | [backend-testing.md](./validation-and-debugging/backend-testing.md) | pytest, fixtures, mocking, coverage |
| Frontend Testing | [frontend-testing.md](./validation-and-debugging/frontend-testing.md) | Playwright E2E, test specs |
| dbt Testing | [dbt-testing.md](./validation-and-debugging/dbt-testing.md) | Schema tests, data validation |
| Data Quality | [data-quality.md](./validation-and-debugging/data-quality.md) | 7 automated quality checks |
| Security | [security-audit.md](./validation-and-debugging/security-audit.md) | OWASP, RLS, auth, hardening |
| Debugging | [debugging-runbook.md](./validation-and-debugging/debugging-runbook.md) | Troubleshooting guide |
| Performance | [performance-testing.md](./validation-and-debugging/performance-testing.md) | Benchmarks, optimization |

---

## Android App

| Document | Description |
|----------|-------------|
| [Implementation Plan](./android-app/implementation-plan.md) | Full Android app implementation plan (Kotlin, Jetpack Compose, Hilt, Ktor, Room) |

---

## Reports & Reviews

| Document | Description |
|----------|-------------|
| [The Great Fix](../reports/The%20Great%20Fix.md) | 10 CRITICAL + 29 HIGH findings resolved |
| [Project Review (Opus)](../reports/PROJECT_REVIEW_OPUS.md) | Full architecture review |
| [Enhancement 3 Plan](../reports/Enhancement%203%20-%20Analytics%20Dashboard%20Upgrades.md) | Dashboard upgrade specs |
| [Architecture Flowchart](../reports/architecture-flowchart.md) | Visual architecture diagrams |

---

## Archive

Historical planning documents from early development phases are preserved in [`docs/archive/`](../archive/).
