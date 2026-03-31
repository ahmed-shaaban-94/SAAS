"""Tests for datapulse.bronze.loader — core functions without a real DB or Excel files."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from datapulse.bronze.column_map import COLUMN_MAP
from datapulse.bronze.loader import (
    ALLOWED_COLUMNS,
    _create_engine,
    _validate_columns,
    discover_files,
    extract_quarter,
    load_to_postgres,
    rename_columns,
    run,
    run_migrations,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_engine() -> MagicMock:
    """Build a minimal SQLAlchemy engine mock with a context-manager conn."""
    engine = MagicMock()
    conn = MagicMock()
    conn.execute.return_value = None
    engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine


def _whitelisted_df(rows: int = 5) -> pl.DataFrame:
    """Minimal DataFrame with only whitelisted column names."""
    return pl.DataFrame(
        {
            "reference_no": [f"REF{i:04d}" for i in range(rows)],
            "date": ["2023-01-01"] * rows,
            "quantity": list(range(rows)),
        }
    )


def _sample_pipeline_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "reference_no": ["REF0001", "REF0002"],
            "date": ["2023-01-01", "2023-01-02"],
            "quantity": [1, 2],
            "source_file": ["Q1.2023.xlsx", "Q1.2023.xlsx"],
            "source_quarter": ["Q1.2023", "Q1.2023"],
        }
    )


# ---------------------------------------------------------------------------
# _validate_columns
# ---------------------------------------------------------------------------


class TestValidateColumns:
    def test_passes_with_a_sample_of_allowed_columns(self):
        cols = list(ALLOWED_COLUMNS)[:5]
        _validate_columns(cols)  # must not raise

    def test_passes_with_source_file_and_source_quarter(self):
        _validate_columns(["source_file", "source_quarter"])

    def test_passes_with_full_allowed_set(self):
        _validate_columns(list(ALLOWED_COLUMNS))

    def test_raises_on_single_unknown_column(self):
        with pytest.raises(ValueError, match="not in whitelist"):
            _validate_columns(["injected_column"])

    def test_error_message_names_every_bad_column(self):
        bad = ["bad_one", "bad_two"]
        with pytest.raises(ValueError) as exc_info:
            _validate_columns(bad)
        msg = str(exc_info.value)
        assert "bad_one" in msg
        assert "bad_two" in msg

    def test_passes_on_empty_list(self):
        _validate_columns([])  # nothing to reject

    def test_raises_when_mix_of_valid_and_invalid(self):
        good = list(ALLOWED_COLUMNS)[0]
        with pytest.raises(ValueError, match="not in whitelist"):
            _validate_columns([good, "sql_injection; DROP TABLE bronze.sales;--"])

    def test_allowed_columns_is_immutable_frozenset(self):
        with pytest.raises((AttributeError, TypeError)):
            ALLOWED_COLUMNS.add("anything")  # type: ignore[attr-defined]

    def test_allowed_columns_contains_source_file(self):
        assert "source_file" in ALLOWED_COLUMNS

    def test_allowed_columns_contains_source_quarter(self):
        assert "source_quarter" in ALLOWED_COLUMNS

    def test_allowed_columns_contains_all_column_map_values(self):
        for db_col in COLUMN_MAP.values():
            assert db_col in ALLOWED_COLUMNS


# ---------------------------------------------------------------------------
# extract_quarter
# ---------------------------------------------------------------------------


class TestExtractQuarter:
    def test_extracts_q1_2023(self):
        assert extract_quarter("Q1.2023.xlsx") == "Q1.2023"

    def test_extracts_q4_2025(self):
        assert extract_quarter("Q4.2025.xlsx") == "Q4.2025"

    def test_falls_back_to_stem_when_no_match(self):
        assert extract_quarter("sales_data.xlsx") == "sales_data"

    def test_prefix_before_quarter_breaks_regex_returns_stem(self):
        # Regex is anchored at start — a prefix means no match → returns stem
        result = extract_quarter("export_Q2.2024.xlsx")
        assert result == "export_Q2.2024"

    def test_filename_without_extension(self):
        assert extract_quarter("Q3.2022") == "Q3.2022"

    def test_all_four_quarters_match(self):
        for q in ("Q1", "Q2", "Q3", "Q4"):
            assert extract_quarter(f"{q}.2023.xlsx") == f"{q}.2023"


# ---------------------------------------------------------------------------
# rename_columns
# ---------------------------------------------------------------------------


class TestRenameColumns:
    def test_renames_known_excel_columns(self):
        df = pl.DataFrame({"Date": ["2023-01-01"], "Material": ["ABC"]})
        result = rename_columns(df)
        assert "date" in result.columns
        assert "material" in result.columns

    def test_ignores_columns_not_in_column_map(self):
        df = pl.DataFrame({"Date": ["2023-01-01"], "Unknown_Col": ["x"]})
        result = rename_columns(df)
        assert "Unknown_Col" in result.columns
        assert "date" in result.columns

    def test_returns_new_dataframe(self):
        df = pl.DataFrame({"Date": ["2023-01-01"]})
        result = rename_columns(df)
        assert result is not df

    def test_does_not_modify_original(self):
        df = pl.DataFrame({"Date": ["2023-01-01"]})
        original_cols = df.columns[:]
        rename_columns(df)
        assert df.columns == original_cols


# ---------------------------------------------------------------------------
# discover_files
# ---------------------------------------------------------------------------


class TestDiscoverFiles:
    def test_returns_sorted_xlsx_files(self, tmp_path):
        for name in ("Q2.2023.xlsx", "Q1.2023.xlsx", "Q3.2023.xlsx"):
            (tmp_path / name).write_bytes(b"x")

        files = discover_files(tmp_path)

        assert len(files) == 3
        assert files[0].name == "Q1.2023.xlsx"
        assert files[1].name == "Q2.2023.xlsx"
        assert files[2].name == "Q3.2023.xlsx"

    def test_ignores_non_xlsx_files(self, tmp_path):
        (tmp_path / "Q1.2023.xlsx").write_bytes(b"x")
        (tmp_path / "readme.txt").write_text("ignore me")
        (tmp_path / "data.csv").write_text("ignore me")

        files = discover_files(tmp_path)
        assert len(files) == 1

    def test_raises_when_no_xlsx_found(self, tmp_path):
        (tmp_path / "notes.txt").write_text("nothing here")
        with pytest.raises(FileNotFoundError, match="No .xlsx files found"):
            discover_files(tmp_path)

    def test_raises_on_empty_directory(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            discover_files(tmp_path)

    def test_returns_path_objects(self, tmp_path):
        (tmp_path / "Q1.2023.xlsx").write_bytes(b"x")
        files = discover_files(tmp_path)
        assert all(isinstance(f, Path) for f in files)

    def test_single_file_returned_as_list(self, tmp_path):
        (tmp_path / "Q1.2023.xlsx").write_bytes(b"x")
        files = discover_files(tmp_path)
        assert len(files) == 1


# ---------------------------------------------------------------------------
# _create_engine
# ---------------------------------------------------------------------------


class TestCreateEngine:
    def test_passes_url_as_first_positional_arg(self):
        url = "postgresql://user:pass@localhost:5432/testdb"
        with patch("datapulse.bronze.loader.create_engine") as mock_ce:
            mock_ce.return_value = MagicMock()
            _create_engine(url)
            call_args = mock_ce.call_args
            assert call_args[0][0] == url

    def test_returns_engine_from_create_engine(self):
        fake_engine = MagicMock()
        with patch("datapulse.bronze.loader.create_engine", return_value=fake_engine):
            result = _create_engine("postgresql://localhost/db")
        assert result is fake_engine

    def test_pool_size_is_2(self):
        with patch("datapulse.bronze.loader.create_engine") as mock_ce:
            mock_ce.return_value = MagicMock()
            _create_engine("postgresql://localhost/db")
            _, kwargs = mock_ce.call_args
            assert kwargs["pool_size"] == 2

    def test_max_overflow_is_0(self):
        with patch("datapulse.bronze.loader.create_engine") as mock_ce:
            mock_ce.return_value = MagicMock()
            _create_engine("postgresql://localhost/db")
            _, kwargs = mock_ce.call_args
            assert kwargs["max_overflow"] == 0

    def test_pool_timeout_is_30(self):
        with patch("datapulse.bronze.loader.create_engine") as mock_ce:
            mock_ce.return_value = MagicMock()
            _create_engine("postgresql://localhost/db")
            _, kwargs = mock_ce.call_args
            assert kwargs["pool_timeout"] == 30

    def test_statement_timeout_in_connect_args(self):
        with patch("datapulse.bronze.loader.create_engine") as mock_ce:
            mock_ce.return_value = MagicMock()
            _create_engine("postgresql://localhost/db")
            _, kwargs = mock_ce.call_args
            assert "statement_timeout" in kwargs["connect_args"]["options"]


# ---------------------------------------------------------------------------
# run_migrations
# ---------------------------------------------------------------------------


class TestRunMigrations:
    """Test run_migrations() — the multi-step migration orchestrator.

    run_migrations() works as follows:
      1. Resolves <repo-root>/migrations/  via Path(__file__).parent * 4
      2. If the directory does not exist, logs a warning and returns early.
      3. Bootstraps the tracking table by running 000_create_schema_migrations.sql
         (if it exists) without any idempotency check.
      4. Discovers every *.sql file in the migrations dir (sorted).
      5. For each file: checks public.schema_migrations; skips if already applied;
         otherwise executes the SQL and records it.

    Strategy: patch `datapulse.bronze.loader.Path` so that the first call
    (Path(__file__)) chains through four .parent steps and a / operator to return
    a controlled fake migrations-dir mock.
    """

    def _make_migrations_dir(self, is_dir: bool, sql_files: list[str] | None = None):
        """Build a fake migrations-dir MagicMock.

        Args:
            is_dir: Whether migrations_dir.is_dir() returns True.
            sql_files: List of filenames returned by migrations_dir.glob("*.sql").
                       Each file mock has .exists() == True and .read_text() returning "SELECT 1;".
        """
        fake_dir = MagicMock()
        fake_dir.is_dir.return_value = is_dir

        # Build per-file mocks
        file_mocks: list[MagicMock] = []
        for name in sql_files or []:
            f = MagicMock(spec=Path)
            f.name = name
            f.exists.return_value = True
            f.read_text.return_value = "SELECT 1;"
            file_mocks.append(f)

        # bootstrap (000) is accessed via / operator on the dir
        bootstrap = MagicMock(spec=Path)
        bootstrap.name = "000_create_schema_migrations.sql"
        bootstrap.exists.return_value = bool(file_mocks)
        bootstrap.read_text.return_value = (
            "CREATE TABLE IF NOT EXISTS public.schema_migrations(filename text);"
        )

        # / "000_..." returns bootstrap; / anything-else is unused in constructor
        def truediv_side_effect(arg):
            if "000" in str(arg):
                return bootstrap
            return MagicMock()

        fake_dir.__truediv__ = MagicMock(side_effect=truediv_side_effect)
        fake_dir.glob.return_value = sorted(file_mocks, key=lambda m: m.name)

        return fake_dir, bootstrap, file_mocks

    def _patch_path_to_dir(self, fake_dir):
        """Context manager: patch loader.Path so it resolves to fake_dir."""
        mock_path_instance = MagicMock()
        (mock_path_instance.parent.parent.parent.parent.__truediv__.return_value) = fake_dir
        return patch("datapulse.bronze.loader.Path", return_value=mock_path_instance)

    def _conn_with_no_prior_migrations(self, engine: MagicMock) -> MagicMock:
        """Configure conn.execute so fetchone() always returns None (no prior migration)."""
        conn = engine.begin.return_value.__enter__.return_value
        result_mock = MagicMock()
        result_mock.fetchone.return_value = None
        conn.execute.return_value = result_mock
        return conn

    # ------------------------------------------------------------------
    # Early-exit: migrations directory does not exist
    # ------------------------------------------------------------------

    def test_returns_early_when_migrations_dir_missing(self):
        fake_dir, _, _ = self._make_migrations_dir(is_dir=False)
        engine = _mock_engine()

        with self._patch_path_to_dir(fake_dir):
            run_migrations(engine)  # must not raise

        engine.begin.assert_not_called()

    # ------------------------------------------------------------------
    # Bootstrap (000) file handling
    # ------------------------------------------------------------------

    def test_executes_bootstrap_sql_when_000_file_exists(self):
        fake_dir, bootstrap, _ = self._make_migrations_dir(
            is_dir=True, sql_files=["000_create_schema_migrations.sql"]
        )
        bootstrap.exists.return_value = True
        engine = _mock_engine()
        conn = self._conn_with_no_prior_migrations(engine)

        with self._patch_path_to_dir(fake_dir):
            run_migrations(engine)

        # At minimum conn.execute must have been called (bootstrap + migration loop)
        assert conn.execute.call_count >= 1

    def test_skips_bootstrap_when_000_file_absent(self):
        fake_dir, bootstrap, _ = self._make_migrations_dir(is_dir=True, sql_files=[])
        bootstrap.exists.return_value = False
        engine = _mock_engine()

        with self._patch_path_to_dir(fake_dir):
            run_migrations(engine)

        # No files → engine.begin may or may not be called for loop (0 iterations)
        # Key assertion: no crash

    def test_re_raises_when_bootstrap_sql_fails(self):
        fake_dir, bootstrap, _ = self._make_migrations_dir(
            is_dir=True, sql_files=["000_create_schema_migrations.sql"]
        )
        bootstrap.exists.return_value = True
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value
        conn.execute.side_effect = RuntimeError("bootstrap failed")

        with (
            self._patch_path_to_dir(fake_dir),
            pytest.raises(RuntimeError, match="bootstrap failed"),
        ):
            run_migrations(engine)

    # ------------------------------------------------------------------
    # Migration-loop behaviour
    # ------------------------------------------------------------------

    def test_skips_already_applied_migration(self):
        fake_dir, bootstrap, file_mocks = self._make_migrations_dir(
            is_dir=True, sql_files=["001_create_bronze_schema.sql"]
        )
        bootstrap.exists.return_value = False  # skip bootstrap for simplicity
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value

        # fetchone returns a row → migration already applied
        applied_result = MagicMock()
        applied_result.fetchone.return_value = ("001_create_bronze_schema.sql",)
        conn.execute.return_value = applied_result

        with self._patch_path_to_dir(fake_dir):
            run_migrations(engine)

        # execute called once (SELECT check), but INSERT never called
        select_calls = [str(c) for c in conn.execute.call_args_list]
        insert_calls = [c for c in select_calls if "INSERT" in c]
        assert len(insert_calls) == 0

    def test_re_raises_when_migration_sql_fails(self):
        fake_dir, bootstrap, _ = self._make_migrations_dir(
            is_dir=True, sql_files=["001_create_bronze_schema.sql"]
        )
        bootstrap.exists.return_value = False
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value

        # First call (SELECT check) returns None → not applied
        # Second call (execute migration SQL) raises
        not_applied = MagicMock()
        not_applied.fetchone.return_value = None
        conn.execute.side_effect = [not_applied, RuntimeError("sql error")]

        with self._patch_path_to_dir(fake_dir), pytest.raises(RuntimeError, match="sql error"):
            run_migrations(engine)


# ---------------------------------------------------------------------------
# load_to_postgres
# ---------------------------------------------------------------------------


class TestLoadToPostgres:
    def test_returns_total_row_count(self):
        df = _whitelisted_df(10)
        engine = _mock_engine()
        result = load_to_postgres(df, engine, batch_size=100)
        assert result == 10

    def test_inserts_all_rows_in_one_batch_when_batch_larger_than_rows(self):
        df = _whitelisted_df(5)
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value

        load_to_postgres(df, engine, batch_size=100)

        assert conn.execute.call_count == 1

    def test_splits_into_correct_number_of_batches(self):
        df = _whitelisted_df(10)
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value

        load_to_postgres(df, engine, batch_size=3)

        # 10 rows / 3 per batch = ceil(10/3) = 4 batches
        assert conn.execute.call_count == 4

    def test_excludes_id_column_from_insert(self):
        df = _whitelisted_df(3).with_columns(pl.lit(None).alias("id"))
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value

        load_to_postgres(df, engine, batch_size=100)

        executed_sql = str(conn.execute.call_args[0][0])
        assert '"id"' not in executed_sql or ":id" not in executed_sql

    def test_excludes_loaded_at_column_from_insert(self):
        df = _whitelisted_df(3).with_columns(pl.lit("2023-01-01").alias("loaded_at"))
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value

        load_to_postgres(df, engine, batch_size=100)

        executed_sql = str(conn.execute.call_args[0][0])
        assert "loaded_at" not in executed_sql

    def test_raises_on_column_not_in_whitelist(self):
        df = pl.DataFrame({"bad_column_name": ["x", "y"]})
        engine = _mock_engine()
        with pytest.raises(ValueError, match="not in whitelist"):
            load_to_postgres(df, engine, batch_size=100)

    def test_raises_on_sql_injection_attempt_in_column_name(self):
        df = pl.DataFrame({"ref; DROP TABLE bronze.sales;--": ["x"]})
        engine = _mock_engine()
        with pytest.raises(ValueError, match="not in whitelist"):
            load_to_postgres(df, engine, batch_size=100)

    def test_returns_zero_for_empty_dataframe(self):
        df = pl.DataFrame({"reference_no": [], "date": [], "quantity": []})
        engine = _mock_engine()
        result = load_to_postgres(df, engine, batch_size=100)
        assert result == 0

    def test_batch_size_of_one_calls_execute_once_per_row(self):
        df = _whitelisted_df(4)
        engine = _mock_engine()
        conn = engine.begin.return_value.__enter__.return_value

        load_to_postgres(df, engine, batch_size=1)

        assert conn.execute.call_count == 4


# ---------------------------------------------------------------------------
# run (full pipeline — all I/O mocked)
# ---------------------------------------------------------------------------


class TestRun:
    """Integration-level tests for the run() orchestration function.

    Every external call (discover_files, read_and_concat, rename_columns,
    save_parquet, _create_engine, run_migration, load_to_postgres, get_settings)
    is mocked so no real filesystem or database access occurs.
    """

    def _base_patches(self):
        """Return a dict of patches shared by most run() tests."""
        _mod = "datapulse.bronze.loader"
        return {
            f"{_mod}.discover_files": patch(f"{_mod}.discover_files"),
            f"{_mod}.read_and_concat": patch(f"{_mod}.read_and_concat"),
            f"{_mod}.rename_columns": patch(f"{_mod}.rename_columns"),
            f"{_mod}.save_parquet": patch(f"{_mod}.save_parquet"),
            f"{_mod}._create_engine": patch(f"{_mod}._create_engine"),
            f"{_mod}.run_migrations": patch(f"{_mod}.run_migrations"),
            f"{_mod}.load_to_postgres": patch(f"{_mod}.load_to_postgres"),
        }

    def test_skip_db_does_not_create_engine(self, tmp_path):
        df = _sample_pipeline_df()
        with (
            patch(
                "datapulse.bronze.loader.discover_files",
                return_value=[tmp_path / "Q1.2023.xlsx"],
            ),
            patch("datapulse.bronze.loader.read_and_concat", return_value=df),
            patch("datapulse.bronze.loader.rename_columns", return_value=df),
            patch("datapulse.bronze.loader.save_parquet", return_value=tmp_path / "out.parquet"),
            patch("datapulse.bronze.loader._create_engine") as mock_engine,
            patch("datapulse.bronze.loader.run_migrations") as mock_migrate,
            patch("datapulse.bronze.loader.load_to_postgres") as mock_load,
        ):
            run(
                source_dir=tmp_path,
                database_url="postgresql://localhost/test",
                parquet_path=tmp_path / "out.parquet",
                batch_size=1000,
                skip_db=True,
            )
            mock_engine.assert_not_called()
            mock_migrate.assert_not_called()
            mock_load.assert_not_called()

    def test_with_db_calls_migration_then_load(self, tmp_path):
        df = _sample_pipeline_df()
        fake_engine = MagicMock()
        fake_engine.dispose = MagicMock()

        with (
            patch(
                "datapulse.bronze.loader.discover_files",
                return_value=[tmp_path / "Q1.2023.xlsx"],
            ),
            patch("datapulse.bronze.loader.read_and_concat", return_value=df),
            patch("datapulse.bronze.loader.rename_columns", return_value=df),
            patch("datapulse.bronze.loader.save_parquet", return_value=tmp_path / "out.parquet"),
            patch("datapulse.bronze.loader._create_engine", return_value=fake_engine),
            patch("datapulse.bronze.loader.run_migrations") as mock_migrate,
            patch("datapulse.bronze.loader.load_to_postgres", return_value=2) as mock_load,
        ):
            run(
                source_dir=tmp_path,
                database_url="postgresql://localhost/test",
                parquet_path=tmp_path / "out.parquet",
                batch_size=1000,
                skip_db=False,
            )
            mock_migrate.assert_called_once_with(fake_engine)
            mock_load.assert_called_once_with(df, fake_engine, 1000)

    def test_engine_disposed_after_successful_run(self, tmp_path):
        df = _sample_pipeline_df()
        fake_engine = MagicMock()

        with (
            patch(
                "datapulse.bronze.loader.discover_files",
                return_value=[tmp_path / "Q1.2023.xlsx"],
            ),
            patch("datapulse.bronze.loader.read_and_concat", return_value=df),
            patch("datapulse.bronze.loader.rename_columns", return_value=df),
            patch("datapulse.bronze.loader.save_parquet", return_value=tmp_path / "out.parquet"),
            patch("datapulse.bronze.loader._create_engine", return_value=fake_engine),
            patch("datapulse.bronze.loader.run_migrations"),
            patch("datapulse.bronze.loader.load_to_postgres", return_value=2),
        ):
            run(
                source_dir=tmp_path,
                database_url="postgresql://localhost/test",
                parquet_path=tmp_path / "out.parquet",
                batch_size=1000,
                skip_db=False,
            )
            fake_engine.dispose.assert_called_once()

    def test_engine_disposed_even_when_migration_raises(self, tmp_path):
        df = _sample_pipeline_df()
        fake_engine = MagicMock()

        with (
            patch(
                "datapulse.bronze.loader.discover_files",
                return_value=[tmp_path / "Q1.2023.xlsx"],
            ),
            patch("datapulse.bronze.loader.read_and_concat", return_value=df),
            patch("datapulse.bronze.loader.rename_columns", return_value=df),
            patch("datapulse.bronze.loader.save_parquet", return_value=tmp_path / "out.parquet"),
            patch("datapulse.bronze.loader._create_engine", return_value=fake_engine),
            patch("datapulse.bronze.loader.run_migrations", side_effect=RuntimeError("boom")),
            patch("datapulse.bronze.loader.load_to_postgres"),
            pytest.raises(RuntimeError, match="boom"),
        ):
            run(
                source_dir=tmp_path,
                database_url="postgresql://localhost/test",
                parquet_path=tmp_path / "out.parquet",
                batch_size=1000,
                skip_db=False,
            )
        fake_engine.dispose.assert_called_once()

    def test_returns_polars_dataframe(self, tmp_path):
        df = _sample_pipeline_df()
        fake_settings = MagicMock()
        fake_settings.database_url = "postgresql://localhost/test"
        fake_settings.parquet_dir = tmp_path
        fake_settings.bronze_batch_size = 1000

        with (
            patch("datapulse.bronze.loader.get_settings", return_value=fake_settings),
            patch(
                "datapulse.bronze.loader.discover_files",
                return_value=[tmp_path / "Q1.2023.xlsx"],
            ),
            patch("datapulse.bronze.loader.read_and_concat", return_value=df),
            patch("datapulse.bronze.loader.rename_columns", return_value=df),
            patch("datapulse.bronze.loader.save_parquet", return_value=tmp_path / "out.parquet"),
        ):
            result = run(
                source_dir=tmp_path,
                parquet_path=tmp_path / "out.parquet",
                batch_size=1000,
                skip_db=True,
            )
        assert isinstance(result, pl.DataFrame)

    def test_uses_settings_defaults_when_optional_args_omitted(self, tmp_path):
        df = _sample_pipeline_df()
        fake_engine = MagicMock()
        fake_settings = MagicMock()
        fake_settings.database_url = "postgresql://localhost/settings_db"
        fake_settings.parquet_dir = tmp_path
        fake_settings.bronze_batch_size = 25_000

        with (
            patch("datapulse.bronze.loader.get_settings", return_value=fake_settings),
            patch(
                "datapulse.bronze.loader.discover_files",
                return_value=[tmp_path / "Q1.2023.xlsx"],
            ),
            patch("datapulse.bronze.loader.read_and_concat", return_value=df),
            patch("datapulse.bronze.loader.rename_columns", return_value=df),
            patch("datapulse.bronze.loader.save_parquet", return_value=tmp_path / "out.parquet"),
            patch("datapulse.bronze.loader._create_engine", return_value=fake_engine),
            patch("datapulse.bronze.loader.run_migrations"),
            patch("datapulse.bronze.loader.load_to_postgres", return_value=2) as mock_load,
        ):
            run(source_dir=tmp_path, skip_db=False)
            # batch_size must come from fake_settings.bronze_batch_size
            mock_load.assert_called_once_with(df, fake_engine, 25_000)

    def test_parquet_is_always_saved(self, tmp_path):
        df = _sample_pipeline_df()
        fake_settings = MagicMock()
        fake_settings.database_url = "postgresql://localhost/test"
        fake_settings.parquet_dir = tmp_path
        fake_settings.bronze_batch_size = 1000

        with (
            patch("datapulse.bronze.loader.get_settings", return_value=fake_settings),
            patch(
                "datapulse.bronze.loader.discover_files",
                return_value=[tmp_path / "Q1.2023.xlsx"],
            ),
            patch("datapulse.bronze.loader.read_and_concat", return_value=df),
            patch("datapulse.bronze.loader.rename_columns", return_value=df),
            patch(
                "datapulse.bronze.loader.save_parquet",
                return_value=tmp_path / "out.parquet",
            ) as mock_save,
        ):
            run(
                source_dir=tmp_path,
                parquet_path=tmp_path / "out.parquet",
                batch_size=1000,
                skip_db=True,
            )
            mock_save.assert_called_once()
