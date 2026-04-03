# DataPulse Strengthening Plan — Subscription Review

> **Status**: PLANNED
> **Created**: 2026-04-03
> **Scope**: 6 improvement tracks across existing phases

---

## Context

DataPulse has reached a mature state with a complete medallion pipeline, 79+ API endpoints, 13 frontend pages, 9 Android screens, and 97.3% backend test coverage. This plan identifies the **6 highest-impact areas** to strengthen the existing codebase — turning a working project into a **production-grade, interview-ready portfolio piece**.

---

## The 6 Tracks

| # | Track | Priority | Impact | Current Gap |
|---|-------|----------|--------|-------------|
| 1 | [Frontend Testing](./01-frontend-testing.md) | CRITICAL | Proves production discipline | 11 tests for 93 components |
| 2 | [Pipeline Retry & Rollback](./02-pipeline-retry-rollback.md) | HIGH | Real-world engineering pattern | Zero retry logic, no rollback |
| 3 | [Quality Gates Enhancement](./03-quality-gates-enhancement.md) | HIGH | Data engineering maturity | 7 hard-coded checks, no UI config |
| 4 | [Android Feature Parity](./04-android-feature-parity.md) | MEDIUM | Full-stack credibility | Missing 6 screens vs web |
| 5 | [Observability Stack](./05-observability-stack.md) | HIGH | DevOps/SRE readiness | No metrics, no dashboards, no tracing |
| 6 | [API Improvements](./06-api-improvements.md) | MEDIUM | Backend maturity | No cursor pagination, no export, basic filtering |

---

## Execution Order

```
Track 1: Frontend Testing ──────────────────────► (foundation — unlocks CI confidence)
Track 2: Pipeline Retry/Rollback ───────────────► (core backend hardening)
Track 3: Quality Gates Enhancement ─────────────► (builds on Track 2)
Track 5: Observability Stack ───────────────────► (parallel with Track 3)
Track 6: API Improvements ─────────────────────► (after Track 2-3 stabilize)
Track 4: Android Feature Parity ────────────────► (last — depends on API additions)
```

---

## Skills Gained Per Track

| Track | Skills for CV/Interview |
|-------|------------------------|
| Frontend Testing | Component testing, E2E automation, CI/CD integration, TDD |
| Pipeline Retry/Rollback | Distributed systems patterns, saga pattern, fault tolerance |
| Quality Gates | Data quality engineering, rule engines, threshold management |
| Android Parity | Cross-platform development, Kotlin Compose, offline-first |
| Observability | Prometheus, Grafana, structured logging, SRE practices |
| API Improvements | Cursor pagination, content negotiation, API design patterns |

---

## Cost

| Resource | Cost |
|----------|------|
| AI APIs | **$0** (all local or free tier) |
| Infrastructure | **$0** (all Docker self-hosted) |
| Monitoring tools | **$0** (Prometheus + Grafana = open source) |
| Testing tools | **$0** (Playwright + Vitest + pytest = open source) |
