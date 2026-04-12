"""Test that /staff/quota is registered before /staff/{staff_key}.

FastAPI matches routes in registration order. If /staff/{staff_key}
appears first, /staff/quota is matched with staff_key="quota",
causing a 422 validation error.
"""

from __future__ import annotations

from datapulse.api.routes.analytics import router


def test_staff_quota_before_staff_detail():
    """The /staff/quota route MUST come before /staff/{staff_key}."""
    paths = [route.path for route in router.routes if hasattr(route, "path")]
    quota_idx = None
    detail_idx = None
    for i, path in enumerate(paths):
        if "staff/quota" in path:
            quota_idx = i
        if "staff/{staff_key}" in path:
            detail_idx = i

    assert quota_idx is not None, "/staff/quota route not found"
    assert detail_idx is not None, "/staff/{staff_key} route not found"
    assert quota_idx < detail_idx, (
        f"staff/quota (index={quota_idx}) must be registered before "
        f"staff/{{staff_key}} (index={detail_idx}) to avoid route shadowing"
    )
