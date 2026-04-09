"""Tests for datapulse.bronze.loader — validate_columns, discover_files,
extract_quarter, read_and_concat, rename_columns, save_parquet."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from datapulse.bronze.loader import (
    ALLOWED_COLUMNS,
    _validate_columns,
    discover_files,
    extract_quarter,
    read_and_concat,
    rename_columns,
    save_parquet,
)

# ---------------------------------------------------------------------------
# TestValidateColumns
# ---------------------------------------------------------------------------


class TestValidateColumns:
    def test_valid_columns_no_error(self):
        """All columns from ALLOWED_COLUMNS pass without raising."""
        valid = list(ALLOWED_COLUMNS)[:5]
        _validate_columns(valid)  # should not raise

    def test_unknown_column_raises_value_error(self):
        """A column not in the whitelist raises ValueError."""
        with pytest.raises(ValueError, match="not in whitelist"):
            _validate_columns(["bad_column"])

    def test_unknown_column_name_in_message(self):
        """The error message contains the offending column name."""
        with pytest.raises(ValueError, match="injected_col"):
            _validate_columns(["injected_col"])

    def test_empty_list_no_error(self):
        """Empty column list passes without raising."""
        _validate_columns([])  # should not raise

    def test_mix_valid_and_invalid_raises(self):
        """Mix of valid and invalid columns raises; all invalid columns listed."""
        valid_col = next(iter(ALLOWED_COLUMNS))
        with pytest.raises(ValueError) as exc_info:
            _validate_columns([valid_col, "evil_col", "other_evil"])
        msg = str(exc_info.value)
        assert "evil_col" in msg
        assert "other_evil" in msg

    def test_multiple_unknowns_all_reported(self):
        """All unknown column names appear in the error message."""
        with pytest.raises(ValueError) as exc_info:
            _validate_columns(["x", "y", "z"])
        msg = str(exc_info.value)
        assert "x" in msg
        assert "y" in msg
        assert "z" in msg

    def test_source_file_lineage_column_allowed(self):
        """'source_file' lineage column is in the whitelist."""
        _validate_columns(["source_file"])  # should not raise

    def test_source_quarter_lineage_column_allowed(self):
        """'source_quarter' lineage column is in the whitelist."""
        _validate_columns(["source_quarter"])  # should not raise


# ---------------------------------------------------------------------------
# TestDiscoverFiles
# ---------------------------------------------------------------------------


class TestDiscoverFiles:
    def test_empty_dir_raises_file_not_found(self, tmp_path):
        """Empty directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="No .xlsx files"):
            discover_files(tmp_path)

    def test_dir_with_xlsx_returns_list(self, tmp_path):
        """Directory with .xlsx files returns a non-empty list."""
        (tmp_path / "Q1.2023.xlsx").touch()
        result = discover_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "Q1.2023.xlsx"

    def test_dir_with_only_csv_raises(self, tmp_path):
        """Directory with only .csv files raises FileNotFoundError."""
        (tmp_path / "data.csv").touch()
        with pytest.raises(FileNotFoundError):
            discover_files(tmp_path)

    def test_files_sorted_by_name(self, tmp_path):
        """Returned files are sorted alphabetically by name."""
        (tmp_path / "Q3.2023.xlsx").touch()
        (tmp_path / "Q1.2023.xlsx").touch()
        (tmp_path / "Q2.2023.xlsx").touch()
        result = discover_files(tmp_path)
        names = [f.name for f in result]
        assert names == sorted(names)

    def test_multiple_xlsx_files_returned(self, tmp_path):
        """All .xlsx files in the directory are discovered."""
        for q in ("Q1.2023", "Q2.2023", "Q3.2023", "Q4.2023"):
            (tmp_path / f"{q}.xlsx").touch()
        result = discover_files(tmp_path)
        assert len(result) == 4

    def test_non_xlsx_files_excluded(self, tmp_path):
        """Non-.xlsx files are excluded from results."""
        (tmp_path / "Q1.2023.xlsx").touch()
        (tmp_path / "notes.txt").touch()
        (tmp_path / "report.csv").touch()
        result = discover_files(tmp_path)
        assert len(result) == 1

    def test_returns_path_objects(self, tmp_path):
        """Returned list contains Path objects."""
        (tmp_path / "Q1.2023.xlsx").touch()
        result = discover_files(tmp_path)
        assert all(isinstance(f, Path) for f in result)

    def test_nested_xlsx_discovered(self, tmp_path):
        """Files in subdirectories are also discovered (rglob)."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "Q1.2023.xlsx").touch()
        result = discover_files(tmp_path)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# TestExtractQuarter
# ---------------------------------------------------------------------------


class TestExtractQuarter:
    def test_q1_2023(self):
        assert extract_quarter("Q1.2023.xlsx") == "Q1.2023"

    def test_q4_2025(self):
        assert extract_quarter("Q4.2025.xlsx") == "Q4.2025"

    def test_random_file_returns_stem(self):
        """Filename with no quarter pattern returns the stem."""
        assert extract_quarter("random_file.xlsx") == "random_file"

    def test_prefix_match(self):
        """Quarter pattern at start of filename is extracted."""
        assert extract_quarter("Q1.2023_extra.xlsx") == "Q1.2023"

    def test_q2_2024(self):
        assert extract_quarter("Q2.2024.xlsx") == "Q2.2024"

    def test_q3_lowercase_no_match_returns_stem(self):
        """Lowercase 'q' does not match — returns stem."""
        result = extract_quarter("q1.2023.xlsx")
        assert result == "q1.2023"

    def test_no_extension(self):
        """Filename without extension returns full name as stem."""
        result = extract_quarter("Q1.2023")
        assert result == "Q1.2023"

    def test_just_filename_no_quarter(self):
        """Generic filename returns its stem."""
        assert extract_quarter("sales_data.xlsx") == "sales_data"


# ---------------------------------------------------------------------------
# TestReadAndConcat
# ---------------------------------------------------------------------------


class TestReadAndConcat:
    def test_all_files_fail_raises_value_error(self, tmp_path):
        """If all files fail to read, raises ValueError with summary."""
        files = [tmp_path / "Q1.2023.xlsx", tmp_path / "Q2.2023.xlsx"]
        for f in files:
            f.touch()

        with patch(
            "datapulse.bronze.loader.read_single_file",
            side_effect=Exception("read error"),
        ), pytest.raises(ValueError, match="All.*file"):
            read_and_concat(files)

    def test_all_fail_error_message_contains_count(self, tmp_path):
        """ValueError message includes the number of failed files."""
        files = [tmp_path / "Q1.2023.xlsx"]
        files[0].touch()

        with patch(
            "datapulse.bronze.loader.read_single_file",
            side_effect=Exception("boom"),
        ), pytest.raises(ValueError, match="1"):
            read_and_concat(files)

    def test_partial_failure_succeeds(self, tmp_path):
        """One file fails, one succeeds — result contains the successful file."""
        files = [tmp_path / "Q1.2023.xlsx", tmp_path / "Q2.2023.xlsx"]
        for f in files:
            f.touch()

        good_df = pl.DataFrame({"col_a": [1, 2, 3]})

        call_count = {"n": 0}

        def side_effect(fp):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("read error")
            return good_df

        with patch("datapulse.bronze.loader.read_single_file", side_effect=side_effect):
            result = read_and_concat(files)

        assert result.shape[0] == 3

    def test_partial_failure_does_not_raise(self, tmp_path):
        """Partial failure (not all) does not raise an exception."""
        files = [tmp_path / "Q1.2023.xlsx", tmp_path / "Q2.2023.xlsx"]
        for f in files:
            f.touch()

        good_df = pl.DataFrame({"col_a": [1]})
        call_count = {"n": 0}

        def side_effect(fp):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("fail first")
            return good_df

        with patch("datapulse.bronze.loader.read_single_file", side_effect=side_effect):
            result = read_and_concat(files)  # should not raise

        assert result is not None

    def test_all_succeed_concat_rows(self, tmp_path):
        """All files succeed — rows are concatenated correctly."""
        files = [tmp_path / "Q1.2023.xlsx", tmp_path / "Q2.2023.xlsx"]
        for f in files:
            f.touch()

        df_a = pl.DataFrame({"col_a": [1, 2]})
        df_b = pl.DataFrame({"col_a": [3, 4]})
        dfs = [df_a, df_b]
        call_count = {"n": 0}

        def side_effect(fp):
            idx = call_count["n"]
            call_count["n"] += 1
            return dfs[idx]

        with patch("datapulse.bronze.loader.read_single_file", side_effect=side_effect):
            result = read_and_concat(files)

        assert result.shape[0] == 4


# ---------------------------------------------------------------------------
# TestRenameColumns
# ---------------------------------------------------------------------------


class TestRenameColumns:
    def test_known_excel_headers_renamed(self):
        """Known Excel headers are renamed to DB column names."""
        df = pl.DataFrame({"Date": ["2023-01-01"], "Material": ["MAT001"]})
        result = rename_columns(df)
        assert "date" in result.columns
        assert "material" in result.columns
        assert "Date" not in result.columns
        assert "Material" not in result.columns

    def test_unknown_headers_preserved(self):
        """Columns not in COLUMN_MAP are preserved unchanged."""
        df = pl.DataFrame({"unknown_col": [1, 2], "Date": ["2023-01-01", "2023-01-02"]})
        result = rename_columns(df)
        assert "unknown_col" in result.columns
        assert "date" in result.columns

    def test_empty_df_returns_empty(self):
        """Empty DataFrame returns empty DataFrame without error."""
        df = pl.DataFrame()
        result = rename_columns(df)
        assert result.shape == (0, 0)

    def test_all_columns_unchanged_if_no_match(self):
        """DataFrame with no matching Excel headers is unchanged."""
        df = pl.DataFrame({"foo": [1], "bar": [2]})
        result = rename_columns(df)
        assert result.columns == ["foo", "bar"]

    def test_partial_rename(self):
        """Only matching columns are renamed; others stay the same."""
        df = pl.DataFrame({"Date": ["2023-01-01"], "custom_field": ["val"]})
        result = rename_columns(df)
        assert "date" in result.columns
        assert "custom_field" in result.columns

    def test_salse_not_tax_typo_mapping(self):
        """'Salse Not TAX' (typo) is correctly mapped to 'sales_not_tax'."""
        df = pl.DataFrame({"Salse Not TAX": [100.0]})
        result = rename_columns(df)
        assert "sales_not_tax" in result.columns
        assert "Salse Not TAX" not in result.columns

    def test_row_count_preserved(self):
        """Row count is unchanged after rename."""
        df = pl.DataFrame({"Date": ["2023-01-01", "2023-01-02", "2023-01-03"]})
        result = rename_columns(df)
        assert result.shape[0] == 3


# ---------------------------------------------------------------------------
# TestSaveParquet
# ---------------------------------------------------------------------------


class TestSaveParquet:
    def _make_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "material": ["MAT001", "MAT002"],
                "quantity": [10, 20],
                "net_sales": [100.0, 200.0],
            }
        )

    def test_saves_file_to_tmp_path(self, tmp_path):
        """save_parquet creates the file at the given path."""
        out = tmp_path / "output.parquet"
        save_parquet(self._make_df(), out)
        assert out.exists()

    def test_file_exists_after_save(self, tmp_path):
        """The saved file has non-zero size."""
        out = tmp_path / "output.parquet"
        save_parquet(self._make_df(), out)
        assert out.stat().st_size > 0

    def test_returns_correct_path(self, tmp_path):
        """save_parquet returns the output path."""
        out = tmp_path / "output.parquet"
        result = save_parquet(self._make_df(), out)
        assert result == out

    def test_creates_parent_dirs(self, tmp_path):
        """save_parquet creates parent directories if they don't exist."""
        out = tmp_path / "nested" / "dir" / "output.parquet"
        save_parquet(self._make_df(), out)
        assert out.exists()

    def test_parquet_readable(self, tmp_path):
        """The saved Parquet file can be read back with correct row count."""
        out = tmp_path / "output.parquet"
        df = self._make_df()
        save_parquet(df, out)
        loaded = pl.read_parquet(out)
        assert loaded.shape[0] == df.shape[0]

    def test_large_df_saves_correctly(self, tmp_path):
        """A larger DataFrame (1000+ rows) saves and loads correctly."""
        import random

        n = 1500
        df = pl.DataFrame(
            {
                "date": ["2023-01-01"] * n,
                "value": [random.random() for _ in range(n)],
            }
        )
        out = tmp_path / "large.parquet"
        save_parquet(df, out)
        loaded = pl.read_parquet(out)
        assert loaded.shape[0] == n
