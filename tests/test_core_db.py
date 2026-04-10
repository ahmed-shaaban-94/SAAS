"""Tests for datapulse.core.db — engine and session factory singletons."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import datapulse.core.db as db_mod


class TestGetEngine:
    def setup_method(self):
        """Reset module singletons before each test."""
        db_mod._engine = None
        db_mod._session_factory = None

    def teardown_method(self):
        db_mod._engine = None
        db_mod._session_factory = None

    @patch("datapulse.core.db.create_engine")
    @patch("datapulse.core.db.get_settings")
    def test_get_engine_creates_once(self, mock_settings, mock_create):
        settings = MagicMock()
        settings.database_url = "postgresql://test:test@localhost/test"
        settings.db_pool_size = 5
        settings.db_pool_max_overflow = 10
        settings.db_pool_timeout = 30
        settings.db_pool_recycle = 1800
        mock_settings.return_value = settings

        fake_engine = MagicMock()
        mock_create.return_value = fake_engine

        engine1 = db_mod.get_engine()
        engine2 = db_mod.get_engine()

        assert engine1 is fake_engine
        assert engine2 is fake_engine
        mock_create.assert_called_once()

    @patch("datapulse.core.db.create_engine")
    @patch("datapulse.core.db.get_settings")
    def test_get_engine_pool_params(self, mock_settings, mock_create):
        settings = MagicMock()
        settings.database_url = "postgresql://u:p@h/db"
        settings.db_pool_size = 3
        settings.db_pool_max_overflow = 7
        settings.db_pool_timeout = 15
        settings.db_pool_recycle = 900
        mock_settings.return_value = settings
        mock_create.return_value = MagicMock()

        db_mod.get_engine()

        mock_create.assert_called_once_with(
            "postgresql://u:p@h/db",
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=7,
            pool_timeout=15,
            pool_recycle=900,
            use_insertmanyvalues=True,
            insertmanyvalues_page_size=1000,
        )


class TestGetSessionFactory:
    def setup_method(self):
        db_mod._engine = None
        db_mod._session_factory = None

    def teardown_method(self):
        db_mod._engine = None
        db_mod._session_factory = None

    @patch("datapulse.core.db.get_engine")
    @patch("datapulse.core.db.sessionmaker")
    def test_get_session_factory_creates_once(self, mock_sm, mock_engine):
        fake_engine = MagicMock()
        mock_engine.return_value = fake_engine
        fake_factory = MagicMock()
        mock_sm.return_value = fake_factory

        f1 = db_mod.get_session_factory()
        f2 = db_mod.get_session_factory()

        assert f1 is fake_factory
        assert f2 is fake_factory
        mock_sm.assert_called_once_with(bind=fake_engine)
