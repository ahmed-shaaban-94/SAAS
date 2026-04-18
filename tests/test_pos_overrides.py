"""override_token_verifier unit tests — factory returns a callable dep.

Full route-level coverage (action mismatch, replay, signature failure) is
tested as part of the route retrofits in Task 20. At this layer we only
assert the factory behaviour + module imports cleanly.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_override_token_verifier_factory_returns_callable() -> None:
    from datapulse.pos.overrides import override_token_verifier

    dep = override_token_verifier("void")
    assert callable(dep)


def test_override_token_verifier_factories_are_independent() -> None:
    from datapulse.pos.overrides import override_token_verifier

    dep_void = override_token_verifier("void")
    dep_nosale = override_token_verifier("no_sale")
    assert dep_void is not dep_nosale
