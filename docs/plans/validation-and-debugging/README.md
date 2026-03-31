# Validation and Debugging

Comprehensive testing, validation, and debugging guides for the DataPulse platform.

## Purpose

These documents serve as actionable references for:

1. **Running and extending tests** across all layers of the stack
2. **Validating data quality** through the medallion pipeline
3. **Auditing security** controls (auth, RLS, CORS, headers)
4. **Diagnosing issues** with a structured debugging runbook
5. **Measuring performance** against defined baselines

## Documents

| Document | Scope |
|----------|-------|
| [Backend Testing](./backend-testing.md) | Python: pytest, fixtures, mocking, coverage |
| [Frontend Testing](./frontend-testing.md) | Next.js: Playwright E2E, component testing |
| [dbt Testing](./dbt-testing.md) | dbt: schema tests, data tests, source freshness |
| [Data Quality](./data-quality.md) | Pipeline: 7 quality checks, gates, flow |
| [Security Audit](./security-audit.md) | OWASP, RLS, auth, CORS, headers |
| [Debugging Runbook](./debugging-runbook.md) | Troubleshooting across all services |
| [Performance Testing](./performance-testing.md) | API, DB, frontend, pipeline benchmarks |

## Current State

| Layer | Coverage / Status |
|-------|------------------|
| Python backend | 95%+ line coverage (pytest-cov) |
| Frontend E2E | 18+ Playwright specs across 6+ files |
| dbt models | ~40 schema + data tests |
| Data quality | 7 check functions, quality gate logic |
| Security | Keycloak OIDC, tenant-scoped RLS, rate limiting |
| Docker | 8 services, all health-checked |

## Quick Start

```bash
# Backend tests
docker exec -it datapulse-app pytest --cov=src/datapulse --cov-report=term-missing

# Frontend E2E tests
docker compose exec frontend npx playwright test

# dbt tests
docker exec -it datapulse-app dbt test --project-dir /app/dbt --profiles-dir /app/dbt

# All checks in sequence
docker exec -it datapulse-app pytest && \
docker compose exec frontend npx playwright test && \
docker exec -it datapulse-app dbt test --project-dir /app/dbt --profiles-dir /app/dbt
```
