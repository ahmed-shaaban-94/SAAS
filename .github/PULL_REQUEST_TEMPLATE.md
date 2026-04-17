## Summary

<!-- Brief description of what this PR does -->

## Strategic Lever

<!--
Which of the four strategic levers does this PR move? Pick at least one.
If none apply, explain why this work is still worth shipping now.
See docs/superpowers/specs/MASTER_CONVERSATION_REPORT.md for the filter.
-->

- [ ] **Clarity** — narrows product story, sharpens positioning, reduces surface
- [ ] **Trust** — real proof, reliability, data confidence, buyer-readable signals
- [ ] **Activation** — upload-to-insight path, first-value moment, golden path
- [ ] **Monetization** — pilot/demo flow, billing readiness, conversion
- [ ] **None of the above** — explain:

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
