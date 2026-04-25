"""POS desktop staged update policy tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from datapulse.pos.update_policy import CandidateRelease, select_update_policy

pytestmark = pytest.mark.unit


def _release(
    *,
    release_id: int = 1,
    version: str = "1.0.2",
    rollout_scope: str = "selected",
    targets: set[int] | None = None,
    active: bool = True,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> CandidateRelease:
    return CandidateRelease(
        release_id=release_id,
        version=version,
        channel="stable",
        platform="win32",
        rollout_scope=rollout_scope,
        active=active,
        release_notes=None,
        min_schema_version=None,
        max_schema_version=None,
        min_app_version=None,
        starts_at=starts_at,
        ends_at=ends_at,
        target_tenant_ids=frozenset(targets or set()),
    )


def test_selected_rollout_allows_only_target_tenants() -> None:
    policy = select_update_policy(
        [_release(targets={7})],
        tenant_id=7,
        current_version="1.0.1",
    )
    assert policy.allowed is True
    assert policy.update_available is True
    assert policy.version == "1.0.2"

    blocked = select_update_policy(
        [_release(targets={7})],
        tenant_id=8,
        current_version="1.0.1",
    )
    assert blocked.allowed is False
    assert blocked.reason == "no_allowed_update"


def test_all_rollout_allows_any_tenant_after_pilot() -> None:
    policy = select_update_policy(
        [_release(version="1.0.3", rollout_scope="all")],
        tenant_id=42,
        current_version="1.0.1",
    )
    assert policy.allowed is True
    assert policy.version == "1.0.3"
    assert policy.rollout_scope == "all"


def test_policy_ignores_paused_inactive_old_and_out_of_window_releases() -> None:
    now = datetime.now(UTC)
    policy = select_update_policy(
        [
            _release(version="1.0.2", rollout_scope="paused", targets={1}),
            _release(version="1.0.3", active=False, targets={1}),
            _release(version="1.0.0", rollout_scope="all"),
            _release(version="1.0.4", rollout_scope="all", starts_at=now + timedelta(hours=1)),
            _release(version="1.0.5", rollout_scope="all", ends_at=now - timedelta(seconds=1)),
        ],
        tenant_id=1,
        current_version="1.0.1",
        now=now,
    )
    assert policy.allowed is False
    assert policy.update_available is False
