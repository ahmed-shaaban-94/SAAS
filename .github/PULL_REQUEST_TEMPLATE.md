## Summary

<!-- Brief description of what this PR does -->

## Changes

-

## Type

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Documentation
- [ ] Tests

## Test Plan

<!-- How was this tested? -->

## Checklist

- [ ] Code follows project conventions
- [ ] `ruff check` passes
- [ ] Python tests pass (`make test`)
- [ ] E2E tests pass (`make test-e2e`) — if frontend changed
- [ ] dbt tests pass (`make dbt-test`) — if models changed
- [ ] No secrets or credentials committed
- [ ] Migration is idempotent (IF NOT EXISTS guards) — if SQL added
- [ ] Tenant isolation verified (RLS + cache keys) — if data access changed
