"""Integration-layer tests for RLS (Row Level Security) tenant session boundary.

These tests verify that ``get_tenant_session`` in ``datapulse.api.deps``:

  1. Always issues ``SET LOCAL app.tenant_id = :tid`` before yielding the session.
  2. Uses the tenant_id extracted from the authenticated user's JWT claims — never
     a hardcoded value.
  3. Falls back to the default tenant_id ('1') when the claim is absent.
  4. Isolates distinct tenants by producing distinct SET LOCAL calls.

Scope & Limitations
-------------------
These are *integration-layer* tests: they verify the SQL statement construction
and session setup contract enforced by the application code, using ``MagicMock``
to stand in for the SQLAlchemy session.

**True DB-level enforcement** (i.e., confirming that PostgreSQL's RLS policies
actually block cross-tenant rows) requires a live PostgreSQL instance with the
RLS policies applied.  That level of testing is out of scope here but should be
addressed in a future CI stage using a PostgreSQL test-container (e.g. via
``pytest-docker`` or Testcontainers).  A bug in the *policy definition* itself
would not be caught by these tests.
"""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

from datapulse.api.deps import get_tenant_session

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _drain_generator(gen) -> None:
    """Exhaust a generator, suppressing the expected StopIteration."""
    with contextlib.suppress(StopIteration):
        next(gen)


def _first_execute_params(mock_session: MagicMock) -> dict:
    """Return the parameter dict passed to the first session.execute() call."""
    return mock_session.execute.call_args_list[0].args[1]


def _first_execute_sql(mock_session: MagicMock) -> str:
    """Return the SQL text of the first session.execute() call."""
    return mock_session.execute.call_args_list[0].args[0].text


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRLSTenantSessionBoundary:
    """Verify that get_tenant_session correctly wires the RLS SET LOCAL call."""

    # ------------------------------------------------------------------
    # 1. SET LOCAL is called with the correct tenant_id from user claims
    # ------------------------------------------------------------------

    @patch("datapulse.core.db.get_session_factory")
    def test_get_tenant_session_sets_local_tenant_id(self, mock_factory: MagicMock) -> None:
        """SET LOCAL app.tenant_id must be called with the tenant_id from JWT claims."""
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        user = {"tenant_id": "99", "sub": "user-abc"}

        gen = get_tenant_session(user=user)
        session = next(gen)

        assert session is mock_session, "Generator must yield the mock session"

        # At least two execute calls: SET LOCAL tenant_id + SET LOCAL statement_timeout
        assert mock_session.execute.call_count >= 2, (
            "Expected at least 2 execute() calls (tenant_id + statement_timeout)"
        )

        # First call must be the tenant_id SET LOCAL
        sql_text = _first_execute_sql(mock_session)
        assert "app.tenant_id" in sql_text, (
            f"First execute() should set app.tenant_id, got: {sql_text!r}"
        )
        assert _first_execute_params(mock_session) == {"tid": "99"}, (
            "SET LOCAL app.tenant_id must use the tenant_id from JWT claims"
        )

        _drain_generator(gen)
        mock_session.commit.assert_called_once()

    # ------------------------------------------------------------------
    # 2. Fallback to default_tenant_id when JWT claim is absent
    # ------------------------------------------------------------------

    @patch("datapulse.core.db.get_session_factory")
    def test_get_tenant_session_uses_default_when_tenant_id_missing(
        self, mock_factory: MagicMock
    ) -> None:
        """When JWT claims contain no tenant_id, the session must fall back to '1'."""
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        user = {"sub": "anonymous-user"}  # intentionally no tenant_id key

        gen = get_tenant_session(user=user)
        next(gen)

        params = _first_execute_params(mock_session)
        assert params == {"tid": "1"}, (
            f"Missing tenant_id claim must default to '1', got {params!r}"
        )

        _drain_generator(gen)

    # ------------------------------------------------------------------
    # 3. tenant_id comes from claims — not hardcoded
    # ------------------------------------------------------------------

    @patch("datapulse.core.db.get_session_factory")
    def test_get_tenant_session_tenant_id_from_claims_not_hardcoded(
        self, mock_factory: MagicMock
    ) -> None:
        """Two distinct tenant_ids in JWT claims must produce two distinct SET LOCAL calls."""
        mock_session_a = MagicMock()
        mock_session_b = MagicMock()

        # Return a different mock session on successive factory() calls
        mock_factory.return_value = MagicMock(side_effect=[mock_session_a, mock_session_b])

        user_a = {"tenant_id": "10", "sub": "user-a"}
        user_b = {"tenant_id": "20", "sub": "user-b"}

        gen_a = get_tenant_session(user=user_a)
        next(gen_a)

        gen_b = get_tenant_session(user=user_b)
        next(gen_b)

        params_a = _first_execute_params(mock_session_a)
        params_b = _first_execute_params(mock_session_b)

        assert params_a == {"tid": "10"}, f"Tenant A session must use tid='10', got {params_a!r}"
        assert params_b == {"tid": "20"}, f"Tenant B session must use tid='20', got {params_b!r}"
        assert params_a != params_b, (
            "Different tenants must produce different SET LOCAL parameter values"
        )

        _drain_generator(gen_a)
        _drain_generator(gen_b)

    # ------------------------------------------------------------------
    # 4. SET LOCAL is called *before* the session is yielded (not deferred)
    # ------------------------------------------------------------------

    @patch("datapulse.core.db.get_session_factory")
    def test_tenant_session_set_local_called_before_yield(self, mock_factory: MagicMock) -> None:
        """SET LOCAL must be issued during session setup, before the caller receives it.

        The RLS invariant requires that the session context variable is in place
        *before* any query can run.  If SET LOCAL were deferred or called after
        yield, a race window would exist where queries could execute without the
        correct tenant filter.
        """
        mock_session = MagicMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)

        user = {"tenant_id": "55", "sub": "user-pre-yield"}

        gen = get_tenant_session(user=user)

        # Execute count before the caller gets the session
        execute_count_before_yield = mock_session.execute.call_count
        assert execute_count_before_yield == 0, (
            "execute() must not have been called before generator.next()"
        )

        # Advance to the yield point — this should trigger the SET LOCAL calls
        next(gen)

        execute_count_after_yield = mock_session.execute.call_count
        assert execute_count_after_yield >= 2, (
            f"Expected SET LOCAL calls before yield, got {execute_count_after_yield} call(s)"
        )

        # Confirm the tenant_id SET LOCAL was among those calls
        all_params = [
            c.args[1]
            for c in mock_session.execute.call_args_list
            if len(c.args) > 1 and isinstance(c.args[1], dict)
        ]
        assert {"tid": "55"} in all_params, (
            f"SET LOCAL with tid='55' must appear before yield; calls: {all_params!r}"
        )

        _drain_generator(gen)
