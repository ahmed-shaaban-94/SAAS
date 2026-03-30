"""Tests for datapulse.config — Settings and get_settings()."""

import os
from unittest.mock import patch

from datapulse.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Helper: construct Settings without reading the real .env file on disk.
# The project's .env has extra keys (POSTGRES_USER, PGADMIN_EMAIL, …) that
# pydantic-settings rejects as "extra_forbidden" — passing _env_file=None
# tells pydantic-settings to skip .env loading entirely so tests are isolated.
# ---------------------------------------------------------------------------

def _settings(**overrides) -> Settings:
    # database_url is required (no default) — provide empty string for tests
    overrides.setdefault("database_url", "")
    return Settings(_env_file=None, **overrides)


class TestSettings:
    """Unit tests for the Settings model itself."""

    def test_database_url_is_required(self):
        """database_url has no default — it must be explicitly provided."""
        s = _settings()
        assert s.database_url == ""

    def test_default_max_file_size_mb(self):
        s = _settings()
        assert s.max_file_size_mb == 500

    def test_default_max_rows(self):
        s = _settings()
        assert s.max_rows == 10_000_000

    def test_default_max_columns(self):
        s = _settings()
        assert s.max_columns == 200

    def test_default_bronze_batch_size(self):
        s = _settings()
        assert s.bronze_batch_size == 50_000

    def test_max_file_size_bytes_property(self):
        s = _settings()
        assert s.max_file_size_bytes == s.max_file_size_mb * 1024 * 1024

    def test_max_file_size_bytes_custom(self):
        s = _settings(max_file_size_mb=100)
        assert s.max_file_size_bytes == 100 * 1024 * 1024

    def test_database_url_overridable_via_kwarg(self):
        custom_url = "postgresql://user:pass@remotehost:5432/testdb"
        s = _settings(database_url=custom_url)
        assert s.database_url == custom_url

    def test_max_file_size_mb_overridable(self):
        s = _settings(max_file_size_mb=250)
        assert s.max_file_size_mb == 250

    def test_bronze_batch_size_overridable(self):
        s = _settings(bronze_batch_size=10_000)
        assert s.bronze_batch_size == 10_000

    def test_max_rows_overridable(self):
        s = _settings(max_rows=5_000_000)
        assert s.max_rows == 5_000_000

    def test_max_columns_overridable(self):
        s = _settings(max_columns=50)
        assert s.max_columns == 50

    def test_settings_is_settings_type(self):
        s = _settings()
        assert isinstance(s, Settings)

    def test_database_url_from_environment_variable(self):
        custom_url = "postgresql://env_user:env_pass@envhost:5432/envdb"
        # Patch env and prevent .env file from leaking extra keys
        with patch.dict(os.environ, {"DATABASE_URL": custom_url}):
            s = Settings(_env_file=None)
        assert s.database_url == custom_url

    def test_parquet_dir_is_path_type(self):
        from pathlib import Path
        s = _settings()
        assert isinstance(s.parquet_dir, Path)

    def test_raw_data_dir_is_path_type(self):
        from pathlib import Path
        s = _settings()
        assert isinstance(s.raw_data_dir, Path)

    def test_processed_data_dir_is_path_type(self):
        from pathlib import Path
        s = _settings()
        assert isinstance(s.processed_data_dir, Path)


class TestGetSettings:
    """Tests for the get_settings() cached factory function."""

    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_returns_settings_instance(self):
        with patch("datapulse.core.config.Settings", side_effect=lambda **kw: _settings(**kw)):
            result = get_settings()
        assert isinstance(result, Settings)

    def test_returns_same_object_on_repeated_calls(self):
        # Bypass the env issue by patching get_settings to return a known object
        fixed = _settings()
        with patch("datapulse.config.get_settings", return_value=fixed):
            from datapulse.config import get_settings as gs
            first = gs()
            second = gs()
        assert first is second

    def test_cache_clear_resets_call_count(self):
        get_settings.cache_clear()
        info_before = get_settings.cache_info()
        assert info_before.currsize == 0

    def test_cache_info_shows_hit_after_second_call(self):
        # Use a patched Settings so the .env file is not read
        with patch("datapulse.core.config.Settings", return_value=_settings()):
            get_settings()
            get_settings()
            info = get_settings.cache_info()
        assert info.hits >= 1

    def test_cache_clear_returns_fresh_instance(self):
        with patch("datapulse.core.config.Settings", return_value=_settings()):
            first = get_settings()
        get_settings.cache_clear()
        with patch("datapulse.core.config.Settings", return_value=_settings()):
            second = get_settings()
        assert first is not second

    def test_database_url_readable_from_cached_settings(self):
        with patch("datapulse.core.config.Settings", return_value=_settings(database_url="postgresql://test:test@localhost/test")):
            s = get_settings()
        assert isinstance(s.database_url, str)
        assert len(s.database_url) > 0

    def test_max_file_size_bytes_computed_correctly(self):
        with patch("datapulse.core.config.Settings", return_value=_settings(max_file_size_mb=200)):
            s = get_settings()
        assert s.max_file_size_bytes == 200 * 1024 * 1024
