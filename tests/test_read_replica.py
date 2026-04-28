"""Unit tests for the read-replica engine + dependency (#608)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from datapulse.core import db as db_module


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Clear the module-level engine + factory caches before/after each test."""
    db_module._engine = None
    db_module._session_factory = None
    db_module._readonly_engine = None
    db_module._readonly_session_factory = None
    yield
    db_module._engine = None
    db_module._session_factory = None
    db_module._readonly_engine = None
    db_module._readonly_session_factory = None


# ── Engine resolution ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestReplicaEngine:
    def test_readonly_engine_falls_back_to_primary_when_unset(self):
        """No replica URL → get_readonly_engine returns the same instance as get_engine."""
        mock_settings = MagicMock()
        mock_settings.database_replica_url = None

        primary_engine = MagicMock()

        with (
            patch.object(db_module, "get_settings", return_value=mock_settings),
            patch.object(db_module, "get_engine", return_value=primary_engine),
        ):
            result = db_module.get_readonly_engine()

        assert result is primary_engine

    def test_readonly_engine_creates_replica_when_url_set(self):
        mock_settings = MagicMock()
        mock_settings.database_replica_url = "postgresql://replica.example.com/db"
        mock_settings.db_pool_size = 5
        mock_settings.db_pool_max_overflow = 10
        mock_settings.db_pool_timeout = 15
        mock_settings.db_pool_recycle = 1800

        replica_engine = MagicMock(name="replica")

        with (
            patch.object(db_module, "get_settings", return_value=mock_settings),
            patch.object(db_module, "_validate_database_url"),
            patch.object(db_module, "create_engine", return_value=replica_engine) as mock_create,
        ):
            result = db_module.get_readonly_engine()

        assert result is replica_engine
        mock_create.assert_called_once()
        assert mock_create.call_args.args[0] == "postgresql://replica.example.com/db"

    def test_readonly_engine_is_cached(self):
        mock_settings = MagicMock()
        mock_settings.database_replica_url = None

        primary = MagicMock()
        with (
            patch.object(db_module, "get_settings", return_value=mock_settings),
            patch.object(db_module, "get_engine", return_value=primary),
        ):
            first = db_module.get_readonly_engine()
            second = db_module.get_readonly_engine()

        assert first is second

    def test_readonly_session_factory_bound_to_readonly_engine(self):
        mock_settings = MagicMock()
        mock_settings.database_replica_url = None
        primary = MagicMock()

        with (
            patch.object(db_module, "get_settings", return_value=mock_settings),
            patch.object(db_module, "get_engine", return_value=primary),
            patch.object(db_module, "sessionmaker") as mock_sm,
        ):
            db_module.get_readonly_session_factory()

        mock_sm.assert_called_once_with(bind=primary)


# ── get_tenant_session_readonly dependency ───────────────────────────────────


@pytest.mark.unit
class TestGetTenantSessionReadonly:
    def _user(self):
        return {"sub": "u1", "tenant_id": "7", "roles": [], "email": "u@x.com"}

    def test_uses_replica_factory_when_configured(self):
        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = "postgresql://replica/db"

        mock_session = MagicMock()
        mock_primary_factory = MagicMock(return_value=MagicMock())
        mock_replica_factory = MagicMock(return_value=mock_session)

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(auth, "get_readonly_session_factory", return_value=mock_replica_factory),
            patch.object(auth, "get_session_factory", return_value=mock_primary_factory),
        ):
            gen = auth.get_tenant_session_readonly(self._user())
            next(gen)  # execute up to the yield
            # Drain: close + cleanup
            with pytest.raises(StopIteration):
                next(gen)

        mock_replica_factory.assert_called_once()
        mock_primary_factory.assert_not_called()

    def test_falls_back_to_primary_when_unconfigured(self):
        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = None

        mock_session = MagicMock()
        mock_primary_factory = MagicMock(return_value=mock_session)

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(auth, "get_session_factory", return_value=mock_primary_factory),
        ):
            gen = auth.get_tenant_session_readonly(self._user())
            session = next(gen)
            with pytest.raises(StopIteration):
                next(gen)

        assert session is mock_session
        mock_primary_factory.assert_called_once()

    def test_falls_back_to_primary_on_replica_error(self):
        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = "postgresql://replica/db"

        mock_replica_factory = MagicMock(side_effect=SQLAlchemyError("replica down"))
        mock_session = MagicMock()
        mock_primary_factory = MagicMock(return_value=mock_session)

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(auth, "get_readonly_session_factory", return_value=mock_replica_factory),
            patch.object(auth, "get_session_factory", return_value=mock_primary_factory),
        ):
            gen = auth.get_tenant_session_readonly(self._user())
            session = next(gen)
            with pytest.raises(StopIteration):
                next(gen)

        assert session is mock_session
        mock_primary_factory.assert_called_once()

    def test_sets_readonly_transaction_flag_when_using_replica(self):
        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = "postgresql://replica/db"

        mock_session = MagicMock()
        mock_replica_factory = MagicMock(return_value=mock_session)
        mock_primary_factory = MagicMock()

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(auth, "get_readonly_session_factory", return_value=mock_replica_factory),
            patch.object(auth, "get_session_factory", return_value=mock_primary_factory),
        ):
            gen = auth.get_tenant_session_readonly(self._user())
            next(gen)
            with pytest.raises(StopIteration):
                next(gen)

        sql_calls = [str(call.args[0]) for call in mock_session.execute.call_args_list]
        assert any("default_transaction_read_only = on" in c for c in sql_calls)

    def test_does_not_set_readonly_flag_when_falling_back(self):
        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = None
        mock_session = MagicMock()

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(
                auth, "get_session_factory", return_value=MagicMock(return_value=mock_session)
            ),
        ):
            gen = auth.get_tenant_session_readonly(self._user())
            next(gen)
            with pytest.raises(StopIteration):
                next(gen)

        sql_calls = [str(call.args[0]) for call in mock_session.execute.call_args_list]
        assert not any("default_transaction_read_only" in c for c in sql_calls)

    def test_sets_tenant_id_and_statement_timeout(self):
        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = None
        mock_session = MagicMock()

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(
                auth, "get_session_factory", return_value=MagicMock(return_value=mock_session)
            ),
        ):
            gen = auth.get_tenant_session_readonly(self._user())
            next(gen)
            with pytest.raises(StopIteration):
                next(gen)

        sql_calls = [str(call.args[0]) for call in mock_session.execute.call_args_list]
        assert any("app.tenant_id" in c for c in sql_calls)
        assert any("statement_timeout" in c for c in sql_calls)

    def test_commits_and_closes_on_success(self):
        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = None
        mock_session = MagicMock()

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(
                auth, "get_session_factory", return_value=MagicMock(return_value=mock_session)
            ),
        ):
            gen = auth.get_tenant_session_readonly(self._user())
            next(gen)
            with pytest.raises(StopIteration):
                next(gen)

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_rolls_back_on_sqlalchemy_error_during_yield(self):
        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = None
        mock_session = MagicMock()

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(
                auth, "get_session_factory", return_value=MagicMock(return_value=mock_session)
            ),
        ):
            gen = auth.get_tenant_session_readonly(self._user())
            next(gen)
            with pytest.raises(SQLAlchemyError):
                gen.throw(SQLAlchemyError("boom"))

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_missing_tenant_id_raises_401(self):
        """Audit M1 (readonly twin): same loud-fail rule applies to the
        replica path — silent fallback to tenant ``"1"`` would be the same
        cross-tenant exposure on read endpoints.
        """
        from fastapi import HTTPException

        from datapulse.core import auth

        mock_settings = MagicMock()
        mock_settings.database_replica_url = None
        mock_factory = MagicMock()

        with (
            patch.object(auth, "get_settings", return_value=mock_settings),
            patch.object(auth, "get_session_factory", return_value=mock_factory),
        ):
            gen = auth.get_tenant_session_readonly({"sub": "u1"})  # no tenant_id
            try:
                next(gen)
            except HTTPException as exc:
                assert exc.status_code == 401
                assert exc.detail == "tenant_id claim missing"
            else:
                raise AssertionError("expected HTTPException(401)")

        mock_factory.assert_not_called()
