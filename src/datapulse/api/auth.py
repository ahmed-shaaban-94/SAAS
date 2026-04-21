"""Authentication and authorization — thin re-export shim.

Canonical home: :mod:`datapulse.core.auth`. This module survives only for
backwards compatibility with callers (including tests using
``app.dependency_overrides``) that import ``get_current_user`` and friends
from ``datapulse.api.auth``. New code should import from
``datapulse.core.auth`` directly. Tracked in issue #541.
"""

from datapulse.core.auth import (
    UserClaims,
    get_current_user,
    get_optional_user,
    get_optional_user_for_health,
    require_api_key,
    require_pipeline_token,
)

__all__ = [
    "UserClaims",
    "get_current_user",
    "get_optional_user",
    "get_optional_user_for_health",
    "require_api_key",
    "require_pipeline_token",
]
