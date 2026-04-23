# Layer boundaries — pointer

Full spec in `docs/CONVENTIONS/layer-boundaries.md`.

Summary: no upward imports; routes → services → repositories (never cross); dependency injection via `get_tenant_session`; `stg_*` dbt models only reference sources; dims/facts only reference `stg_*`; aggs only reference dims/facts.

Violation = fail. If unsure, read the full spec.
