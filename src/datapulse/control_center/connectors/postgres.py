"""PostgresConnector — implements SourceConnector for postgres sources.

Connects to a tenant-owned PostgreSQL database using psycopg2.
Passwords are NEVER stored in config_json — they are loaded at runtime
from source_credentials via credentials.py.

config_json shape for postgres connections:
    {
        "host":     "db.example.com",
        "port":     5432,
        "database": "sales_db",
        "user":     "readonly_user",
        "schema":   "public",      # optional, defaults to "public"
        "table":    "orders"       # required for preview
    }

Security:
  - The password is loaded via load_credential() immediately before use
    and is never stored in this object or any config dict.
  - A missing or empty CONTROL_CENTER_CREDS_KEY causes an immediate error.
  - Table/schema identifiers are validated against a strict allowlist
    before being interpolated into SQL.
"""

from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy.orm import Session

from datapulse.control_center.models import (
    ConnectionPreviewResult,
    ConnectionTestResult,
    PreviewColumn,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

# Identifier allowlist: letters, digits, underscore, dollar sign only.
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

_DEFAULT_CONNECT_TIMEOUT = 5  # seconds


def _validate_identifier(value: str, field: str) -> str:
    """Raise ValueError if ``value`` is not a safe SQL identifier."""
    if not value or not _SAFE_IDENTIFIER.match(value):
        raise ValueError(
            f"postgres_connector: unsafe {field} '{value}' — "
            "only letters, digits, underscores, and $ are allowed"
        )
    return value


class PostgresConnector:
    """Connector for PostgreSQL source type.

    Requires the credential (password) to be stored in source_credentials.
    Accepts an optional SQLAlchemy session so the connector can load the
    credential.  When session is None (e.g. during bare testing), the
    caller must supply the password via config["_password"] (test only).
    """

    def __init__(
        self,
        session: Session | None = None,
        *,
        connection_id: int = 0,
        tenant_id: int = 0,
    ) -> None:
        self._session = session
        self._connection_id = connection_id
        self._tenant_id = tenant_id

    # ── Protocol implementation ──────────────────────────────

    def test(self, *, tenant_id: int, config: dict) -> ConnectionTestResult:
        """Connect to the Postgres database and run SELECT 1.

        Loads the password at runtime from source_credentials.
        Returns ConnectionTestResult with ok=True on success.
        """
        try:
            password = self._load_password(tenant_id, config)
        except ValueError as exc:
            return ConnectionTestResult(ok=False, error=str(exc))

        try:
            import psycopg2  # noqa: PLC0415 — lazy import keeps startup fast
        except ImportError:
            return ConnectionTestResult(
                ok=False,
                error="psycopg2 is not installed — add it to requirements.txt",
            )

        host = config.get("host", "")
        port = int(config.get("port", 5432))
        database = config.get("database", "")
        user = config.get("user", "")

        if not host or not database or not user:
            return ConnectionTestResult(ok=False, error="config_missing_host_database_or_user")

        try:
            t0 = time.perf_counter()
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password,
                connect_timeout=_DEFAULT_CONNECT_TIMEOUT,
            )
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.close()
            finally:
                conn.close()
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        except Exception as exc:  # noqa: BLE001
            return ConnectionTestResult(ok=False, error=f"connection_failed: {exc}")

        log.info(
            "postgres_connector_test_ok",
            tenant_id=tenant_id,
            host=host,
            database=database,
        )
        return ConnectionTestResult(ok=True, latency_ms=latency_ms)

    def preview(
        self,
        *,
        tenant_id: int,
        config: dict,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> ConnectionPreviewResult:
        """Run SELECT * FROM {schema}.{table} LIMIT {max_rows} and return metadata.

        Identifiers are validated before interpolation — no SQL injection possible.
        Password is loaded from source_credentials at runtime.

        Returns:
            ConnectionPreviewResult with column metadata and sample rows.

        Raises:
            ValueError: On bad config, missing credentials, or identifier validation failure.
        """
        try:
            password = self._load_password(tenant_id, config)
        except ValueError:
            raise

        try:
            import psycopg2  # noqa: PLC0415
            import psycopg2.extras  # noqa: PLC0415
        except ImportError as exc:
            raise ValueError("psycopg2 is not installed") from exc

        host = config.get("host", "")
        port = int(config.get("port", 5432))
        database = config.get("database", "")
        user = config.get("user", "")
        schema = config.get("schema", "public") or "public"
        table = config.get("table", "")

        if not host or not database or not user or not table:
            raise ValueError("config_missing_host_database_user_or_table")

        # Validate identifiers before SQL interpolation
        schema = _validate_identifier(schema, "schema")
        table = _validate_identifier(table, "table")

        # Safe to interpolate — identifiers are allowlisted above
        query = f'SELECT * FROM "{schema}"."{table}" LIMIT {max_rows}'  # noqa: S608

        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password,
                connect_timeout=_DEFAULT_CONNECT_TIMEOUT,
            )
            try:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(query)
                all_rows: list[dict[str, Any]] = [dict(r) for r in cur.fetchall()]
                col_names: list[str] = (
                    [desc[0] for desc in cur.description] if cur.description else []
                )
                cur.close()
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"preview_failed: {exc}") from exc

        # Build column metadata
        columns: list[PreviewColumn] = []
        for col in col_names:
            values = [str(r.get(col, "")) for r in all_rows if r.get(col) is not None]
            null_count = sum(1 for r in all_rows if r.get(col) is None)
            columns.append(
                PreviewColumn(
                    source_name=col,
                    detected_type=_detect_type(all_rows, col),
                    null_count=null_count,
                    unique_count=len(set(values)),
                    sample_values=values[:5],
                )
            )

        preview_sample = all_rows[:sample_rows]
        # Stringify all values for JSON safety
        safe_sample: list[dict[str, Any]] = [
            {k: str(v) if v is not None else None for k, v in row.items()} for row in preview_sample
        ]

        total = len(all_rows)
        null_ratios: dict[str, float] = {}
        if total > 0:
            for col in col_names:
                null_count = sum(1 for r in all_rows if r.get(col) is None)
                null_ratios[col] = round(null_count / total, 4)

        return ConnectionPreviewResult(
            columns=columns,
            sample_rows=safe_sample,
            row_count_estimate=total,
            null_ratios=null_ratios,
        )

    # ── Internal helpers ─────────────────────────────────────

    def _load_password(self, tenant_id: int, config: dict) -> str:
        """Load the password from source_credentials (or config["_password"] in tests).

        Raises ValueError when no password is available.
        """
        # Test-only escape hatch — _password is injected by test fixtures only.
        test_pw = config.get("_password")
        if test_pw is not None:
            return str(test_pw)

        if self._session is None:
            raise ValueError("postgres_connector: no session available to load credentials")

        from datapulse.control_center.credentials import load_credential  # noqa: PLC0415

        password = load_credential(
            self._session,
            connection_id=self._connection_id,
            tenant_id=tenant_id,
        )
        if not password:
            raise ValueError(
                "postgres_connector: no stored credential found — "
                "store the password via PATCH /connections/{id} with the credential field"
            )
        return password


def _detect_type(rows: list[dict[str, Any]], col: str) -> str:
    """Heuristic type detection from sample values."""
    values = [r.get(col) for r in rows if r.get(col) is not None]
    if not values:
        return "string"
    sample = values[0]
    if isinstance(sample, bool):
        return "boolean"
    if isinstance(sample, int):
        return "integer"
    if isinstance(sample, float):
        return "numeric"
    return "string"
