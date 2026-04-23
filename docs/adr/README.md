# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) — lightweight documents that capture important architectural decisions made during the project's evolution.

## Format

Each ADR follows this structure:

- **Status**: `Accepted` | `Superseded by ADR-NNN` | `Deprecated`
- **Context**: The situation and forces at play
- **Decision**: What was decided
- **Consequences**: Trade-offs, risks, and follow-up actions

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-auth-strategy.md) | Multi-strategy authentication (Auth0 + API Key + dev fallback) | Accepted | 2026-04-09 |
| [002](002-medallion-architecture.md) | Medallion data architecture with dbt + PostgreSQL | Accepted | 2026-04-09 |
| [003](003-rls-tenant-isolation.md) | Row Level Security for multi-tenant isolation | Accepted | 2026-04-09 |
| [004](004-csp-scoped-to-api.md) | CSP scoped to API routes, not global Nginx | Accepted | 2026-04-09 |
| [005](005-analytics-repository-mixins.md) | Analytics repository split into mixin classes | Accepted | 2026-04-09 |
| [006](006-onboarding-step-taxonomy.md) | Onboarding step taxonomy — setup vs activation | Accepted | 2026-04-18 |
| [007](007-platform-matrix.md) | Platform matrix and React app direction | Accepted | 2026-04-24 |
