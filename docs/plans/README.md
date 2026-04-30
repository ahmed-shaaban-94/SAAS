# DataPulse — Project Plans

> Organized planning documentation for the DataPulse analytics platform.

## Layout

```
plans/
├── active/        # In-flight or proposed plans
├── sprints/       # Dated sprint plans (chronological)
├── specs/         # Design specifications referenced by sprint plans
├── future/        # Roadmap for Phase 5–10
└── completed/     # Historical plans
    └── audits/    # Codename audit-execution plans (Dragon Roar, Iron Curtain, ...)
```

---

## Active Plans

| Plan | Document | Summary |
|------|----------|---------|
| Implementation Plan | [active/implementation-plan.md](./active/implementation-plan.md) | Graph-validated plan companion to the Deep Analysis Report |
| Roadmap Filter | [active/roadmap-filter.md](./active/roadmap-filter.md) | Strategic four-lever planning gate |
| Hardening Sprint | [active/hardening-sprint.md](./active/hardening-sprint.md) | Production-readiness sprint (no new features) |
| Optimization Plan | [active/optimization-plan.md](./active/optimization-plan.md) | Naming fix, core KPIs, forecast pacing, growth decomposition |
| Control Center Roadmap | [active/control-center-roadmap.md](./active/control-center-roadmap.md) | Control Center implementation track |

---

## Sprint Plans

Dated sprint plans under [`sprints/`](./sprints/). Each sprint plan typically pairs with a design spec under [`specs/`](./specs/).

Examples:
- `sprints/2026-04-17-phase2-golden-path.md` — Phase 2 golden path
- `sprints/2026-04-22-egypt-foundation.md` ↔ `specs/2026-04-22-egypt-foundation-design.md`
- `sprints/2026-04-21-home-dashboard-action-center.md` ↔ `specs/2026-04-21-home-dashboard-action-center-design.md`

---

## Future Phases (PLANNED)

| Phase | Document | Priority | Summary |
|-------|----------|----------|---------|
| **5** | [future/phase-5-multi-tenancy.md](./future/phase-5-multi-tenancy.md) | CRITICAL | Tenant onboarding, Stripe, usage metering, admin panel |
| **6** | [future/phase-6-data-sources.md](./future/phase-6-data-sources.md) | HIGH | Google Sheets, DB connectors, API connectors, schema mapping |
| **7** | [future/phase-7-self-service.md](./future/phase-7-self-service.md) | MEDIUM | Dashboard builder, custom reports, exports, alerts |
| **8** | [future/phase-8-ai-intelligence.md](./future/phase-8-ai-intelligence.md) | MEDIUM | NL queries, forecasting, smart alerts, Arabic summaries |
| **9** | [future/phase-9-collaboration.md](./future/phase-9-collaboration.md) | NICE-TO-HAVE | Comments, sharing, team workspaces, activity feed |
| **10** | [future/phase-10-scale-infra.md](./future/phase-10-scale-infra.md) | WHEN NEEDED | K8s, S3, Celery, CDN, monitoring |

See [future/README.md](./future/README.md) for the full roadmap, dependency graph, and risk register.

---

## Completed Phases

Reference documents for shipped work, under [`completed/`](./completed/):

| Phase | Document |
|-------|----------|
| Phase 1 — Data Pipeline | [completed/phase-1-data-pipeline.md](./completed/phase-1-data-pipeline.md) |
| Phase 2 — Automation | [completed/phase-2-automation.md](./completed/phase-2-automation.md) |
| Phase 4 — Public Website | [completed/phase-4-public-website.md](./completed/phase-4-public-website.md) |
| Validation & Debugging | [completed/validation-and-debugging.md](./completed/validation-and-debugging.md) |
| Subscription Plan Review | [completed/subscription-plan-review.md](./completed/subscription-plan-review.md) |
| Wild Wolf Beta Release | [completed/wild-wolf-beta-release.md](./completed/wild-wolf-beta-release.md) |
| Master Audit | [completed/master-audit.md](./completed/master-audit.md) |
| Android App | [completed/android-app.md](./completed/android-app.md) |
| AI-Light LangGraph | [completed/ai-light-langgraph.md](./completed/ai-light-langgraph.md) |

### Codename Audit Plans

Cross-cutting audit-execution plans under [`completed/audits/`](./completed/audits/):

- [Dragon Roar](./completed/audits/dragon-roar.md) — Full project audit execution (data integrity, security, testing)
- [Iron Curtain](./completed/audits/iron-curtain.md) — Hardening plan (auth, exceptions, types, indexes)
- [Market Strike](./completed/audits/market-strike.md) — Competitive features plan (billing, onboarding, RBAC)
- [Unlock the Vault](./completed/audits/unlock-the-vault.md) — Activate already-built features (no new code)

---

## Related

- [Audits](../audit/) — Read-only audit reports (project, bronze, silver, calculation)
- [Reports](../reports/) — Reviews, post-mortems, analyses
