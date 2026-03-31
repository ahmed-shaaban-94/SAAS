"""Tests for SQL Lab validator module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.sql_lab.validator import (
    SQLValidationError,
    get_schema_tables,
    validate_sql,
)

# ---------------------------------------------------------------------------
# validate_sql — empty / missing input
# ---------------------------------------------------------------------------


class TestValidateSqlEmpty:
    """Empty or blank SQL must raise SQLValidationError."""

    def test_none_raises(self):
        with pytest.raises(SQLValidationError, match="empty"):
            validate_sql("")

    def test_whitespace_only_raises(self):
        with pytest.raises(SQLValidationError, match="empty"):
            validate_sql("   \n\t  ")

    def test_empty_string_raises(self):
        with pytest.raises(SQLValidationError, match="empty"):
            validate_sql("")


# ---------------------------------------------------------------------------
# validate_sql — multiple statements
# ---------------------------------------------------------------------------


class TestValidateSqlMultipleStatements:
    """Only a single statement is allowed."""

    def test_two_selects_raise(self):
        with pytest.raises(SQLValidationError, match="single"):
            validate_sql("SELECT 1; SELECT 2")

    def test_select_then_drop_raises(self):
        with pytest.raises(SQLValidationError, match="single"):
            validate_sql("SELECT 1; DROP TABLE foo")


# ---------------------------------------------------------------------------
# validate_sql — allowed statement types
# ---------------------------------------------------------------------------


class TestValidateSqlAllowed:
    """SELECT, WITH (CTE), and EXPLAIN statements must pass."""

    def test_simple_select(self):
        result = validate_sql("SELECT 1")
        assert result == "SELECT 1"

    def test_select_from_table(self):
        result = validate_sql("SELECT * FROM public_marts.dim_date")
        assert "SELECT" in result

    def test_with_cte(self):
        sql = "WITH cte AS (SELECT 1 AS x) SELECT * FROM cte"
        result = validate_sql(sql)
        assert result.upper().startswith("WITH")

    def test_explain_select(self):
        result = validate_sql("EXPLAIN SELECT 1")
        assert result.upper().startswith("EXPLAIN")

    def test_explain_analyze_select(self):
        result = validate_sql("EXPLAIN ANALYZE SELECT 1")
        assert "EXPLAIN" in result.upper()


# ---------------------------------------------------------------------------
# validate_sql — blocked statement types
# ---------------------------------------------------------------------------


class TestValidateSqlBlockedTypes:
    """INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE must raise."""

    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO t VALUES (1)",
            "UPDATE t SET x = 1",
            "DELETE FROM t",
            "DROP TABLE t",
            "ALTER TABLE t ADD COLUMN x INT",
            "CREATE TABLE t (id INT)",
            "TRUNCATE TABLE t",
        ],
        ids=[
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "ALTER",
            "CREATE",
            "TRUNCATE",
        ],
    )
    def test_blocked_type_raises(self, sql: str):
        with pytest.raises(SQLValidationError, match="not allowed"):
            validate_sql(sql)


# ---------------------------------------------------------------------------
# validate_sql — blocked keywords
# ---------------------------------------------------------------------------


class TestValidateSqlBlockedKeywords:
    """Dangerous keywords anywhere in the SQL must raise."""

    @pytest.mark.parametrize(
        "keyword",
        [
            "GRANT",
            "REVOKE",
            "COPY",
            "EXECUTE",
            "CALL",
            "VACUUM",
            "REINDEX",
            "CLUSTER",
            "pg_read_file",
            "pg_write_file",
            "lo_import",
            "lo_export",
        ],
    )
    def test_blocked_keyword_raises(self, keyword: str):
        sql = f"SELECT {keyword}('x')"
        with pytest.raises(SQLValidationError, match="disallowed keyword"):
            validate_sql(sql)

    def test_blocked_keyword_case_insensitive(self):
        with pytest.raises(SQLValidationError, match="disallowed keyword"):
            validate_sql("SELECT grant FROM t")

    def test_do_dollar_blocked(self):
        # DO $$ is caught by the non-SELECT sanity check at the end
        with pytest.raises(SQLValidationError):
            validate_sql("DO $$ BEGIN END $$")

    def test_grant_in_subquery_blocked(self):
        # Blocked keyword inside a subquery still triggers the blocklist
        with pytest.raises(SQLValidationError, match="disallowed keyword"):
            validate_sql("SELECT * FROM (SELECT GRANT FROM t) sub")


# ---------------------------------------------------------------------------
# validate_sql — normalisation (semicolons, whitespace)
# ---------------------------------------------------------------------------


class TestValidateSqlNormalisation:
    """Trailing semicolons are stripped and whitespace is trimmed."""

    def test_trailing_semicolon_stripped(self):
        result = validate_sql("SELECT 1;")
        assert not result.endswith(";")
        assert result == "SELECT 1"

    def test_multiple_trailing_semicolons_parsed_as_multiple(self):
        # sqlparse treats extra semicolons as multiple statements
        with pytest.raises(SQLValidationError, match="single"):
            validate_sql("SELECT 1;;;")

    def test_leading_whitespace_trimmed(self):
        result = validate_sql("   SELECT 1")
        assert result == "SELECT 1"

    def test_trailing_whitespace_trimmed(self):
        result = validate_sql("SELECT 1   ")
        assert result == "SELECT 1"

    def test_mixed_whitespace_and_semicolon(self):
        result = validate_sql("  SELECT 1 ;  ")
        assert result == "SELECT 1"


# ---------------------------------------------------------------------------
# validate_sql — non-SELECT statements (sanity check)
# ---------------------------------------------------------------------------


class TestValidateSqlNonSelect:
    """Statements that don't start with SELECT/WITH/EXPLAIN must raise."""

    def test_set_raises(self):
        with pytest.raises(SQLValidationError):
            validate_sql("SET search_path TO public")

    def test_show_raises(self):
        with pytest.raises(SQLValidationError):
            validate_sql("SHOW server_version")

    def test_begin_raises(self):
        with pytest.raises(SQLValidationError):
            validate_sql("BEGIN")

    def test_commit_raises(self):
        with pytest.raises(SQLValidationError):
            validate_sql("COMMIT")


# ---------------------------------------------------------------------------
# get_schema_tables — mocked session
# ---------------------------------------------------------------------------


class TestGetSchemaTables:
    """get_schema_tables returns correct structure from mocked DB rows."""

    def _mock_session(self, rows: list[tuple]) -> MagicMock:
        session = MagicMock()
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter(rows))
        session.execute.return_value = result
        return session

    def test_returns_list_of_dicts(self):
        rows = [
            ("dim_date", "date_key", "integer", "NO"),
            ("dim_date", "full_date", "date", "NO"),
            ("fct_sales", "sale_id", "bigint", "NO"),
        ]
        session = self._mock_session(rows)
        tables = get_schema_tables(session)

        assert isinstance(tables, list)
        assert len(tables) == 2

    def test_groups_columns_by_table(self):
        rows = [
            ("dim_date", "date_key", "integer", "NO"),
            ("dim_date", "full_date", "date", "NO"),
            ("dim_date", "year", "integer", "YES"),
            ("fct_sales", "sale_id", "bigint", "NO"),
        ]
        session = self._mock_session(rows)
        tables = get_schema_tables(session)

        table_map = {t["table_name"]: t for t in tables}
        assert "dim_date" in table_map
        assert "fct_sales" in table_map
        assert len(table_map["dim_date"]["columns"]) == 3
        assert len(table_map["fct_sales"]["columns"]) == 1

    def test_column_structure(self):
        rows = [
            ("dim_date", "date_key", "integer", "NO"),
        ]
        session = self._mock_session(rows)
        tables = get_schema_tables(session)

        col = tables[0]["columns"][0]
        assert col["column_name"] == "date_key"
        assert col["data_type"] == "integer"
        assert col["is_nullable"] is False

    def test_nullable_yes_maps_to_true(self):
        rows = [
            ("dim_date", "year", "integer", "YES"),
        ]
        session = self._mock_session(rows)
        tables = get_schema_tables(session)

        col = tables[0]["columns"][0]
        assert col["is_nullable"] is True

    def test_empty_result(self):
        session = self._mock_session([])
        tables = get_schema_tables(session)
        assert tables == []

    def test_session_execute_called_once(self):
        session = self._mock_session([])
        get_schema_tables(session)
        session.execute.assert_called_once()
