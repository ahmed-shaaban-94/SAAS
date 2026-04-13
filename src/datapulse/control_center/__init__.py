"""Control Center — unified data control plane.

Manages source connections, pipeline profiles, mapping templates, drafts,
releases, and sync jobs. Implements a Draft → Validate → Preview → Publish
→ Rollback workflow on top of the existing DataPulse pipeline.

Phase 1a: READ-only routes + schema + RBAC permissions (behind feature flag).
"""
