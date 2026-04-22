"""Tests for the nightly RLS enforcement audit (#546)."""

from __future__ import annotations

from unittest.mock import MagicMock

from datapulse.pipeline.rls_audit import (
    AUDITED_SCHEMAS,
    RlsViolation,
    audit_rls_enforcement,
)


def _row(schema: str, table: str, rls: bool, force: bool):
    """Build a pg_class row stub with the fields the audit query selects."""
    r = MagicMock()
    r.schema_name = schema
    r.table_name = table
    r.row_security = rls
    r.force_row_security = force
    return r


def _session_returning(rows: list) -> MagicMock:
    """Session stub whose ``execute().all()`` returns ``rows``."""
    session = MagicMock()
    session.execute.return_value.all.return_value = rows
    return session


class TestAuditRlsEnforcement:
    def test_empty_result_means_no_violations(self):
        session = _session_returning([])
        assert audit_rls_enforcement(session) == []

    def test_returns_violations_as_dataclasses(self):
        session = _session_returning(
            [
                _row("public_marts", "fct_sales", rls=False, force=False),
                _row("public_staging", "stg_sales", rls=True, force=False),
            ]
        )
        result = audit_rls_enforcement(session)
        assert len(result) == 2
        assert isinstance(result[0], RlsViolation)
        assert result[0].fqn == "public_marts.fct_sales"
        assert result[0].row_security is False
        assert result[0].force_row_security is False
        assert result[1].fqn == "public_staging.stg_sales"
        assert result[1].force_row_security is False

    def test_query_uses_audited_schemas_by_default(self):
        session = _session_returning([])
        audit_rls_enforcement(session)
        # Second positional arg to session.execute() is the bind params dict.
        call = session.execute.call_args
        params = call.args[1] if len(call.args) >= 2 else call.kwargs["params"]
        assert params == {"schemas": list(AUDITED_SCHEMAS)}

    def test_custom_schemas_are_passed_through(self):
        session = _session_returning([])
        audit_rls_enforcement(session, schemas=("bronze",))
        call = session.execute.call_args
        params = call.args[1] if len(call.args) >= 2 else call.kwargs["params"]
        assert params == {"schemas": ["bronze"]}
