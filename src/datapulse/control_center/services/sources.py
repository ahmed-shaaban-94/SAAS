"""SourcesService — source connection CRUD, connectivity test, preview, canonical domains."""

from __future__ import annotations

from sqlalchemy.orm import Session

from datapulse.control_center import canonical as canonical_helpers
from datapulse.control_center.models import (
    CanonicalDomain,
    CanonicalDomainList,
    ConnectionPreviewResult,
    ConnectionTestResult,
    SourceConnection,
    SourceConnectionList,
)
from datapulse.control_center.repository import SourceConnectionRepository
from datapulse.logging import get_logger

log = get_logger(__name__)


def _get_connector(source_type: str, *, session=None, connection_id: int = 0, tenant_id: int = 0):  # type: ignore[return]
    """Return the connector instance for a given source_type, or None.

    For credential-aware connectors (postgres, mssql …) the session,
    connection_id, and tenant_id are forwarded so the connector can load
    the password at runtime from source_credentials.
    """
    if source_type == "file_upload":
        from datapulse.control_center.connectors.file_upload import (  # noqa: PLC0415
            FileUploadConnector,
        )

        return FileUploadConnector()
    if source_type == "google_sheets":
        from datapulse.control_center.connectors.google_sheets import (  # noqa: PLC0415
            GoogleSheetsConnector,
        )

        return GoogleSheetsConnector()
    return None


class SourcesService:
    """Source connection CRUD, connectivity test, preview, and canonical domain listing."""

    def __init__(self, session: Session, *, connections: SourceConnectionRepository) -> None:
        self._session = session
        self._connections = connections

    # ── Canonical domains ────────────────────────────────────────────────────

    def list_canonical_domains(self) -> CanonicalDomainList:
        rows = canonical_helpers.list_canonical_domains(self._session)
        return CanonicalDomainList(items=[CanonicalDomain(**r) for r in rows])

    # ── Source connection reads ──────────────────────────────────────────────

    def list_connections(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SourceConnectionList:
        rows, total = self._connections.list(
            source_type=source_type, status=status, page=page, page_size=page_size
        )
        return SourceConnectionList(
            items=[SourceConnection(**r) for r in rows],
            total=total,
        )

    def get_connection(self, connection_id: int) -> SourceConnection | None:
        row = self._connections.get(connection_id)
        return SourceConnection(**row) if row else None

    # ── Source connection writes ─────────────────────────────────────────────

    def create_connection(
        self,
        *,
        tenant_id: int,
        name: str,
        source_type: str,
        config: dict,
        created_by: str | None = None,
    ) -> SourceConnection:
        """Create a new source connection for the current tenant."""
        row = self._connections.create(
            tenant_id=tenant_id,
            name=name,
            source_type=source_type,
            config_json=config,
            created_by=created_by,
        )
        return SourceConnection(**row)

    def update_connection(
        self,
        connection_id: int,
        *,
        tenant_id: int,
        name: str | None = None,
        status: str | None = None,
        config: dict | None = None,
        credential: str | None = None,
    ) -> SourceConnection | None:
        """Update specified fields on an existing connection.

        When ``credential`` is provided (non-empty), it is encrypted and
        persisted in source_credentials, and credentials_ref is updated to
        str(cred_id).  The plain value is never stored in config_json or
        returned in the response.

        Returns None when the connection is not found (or not accessible via RLS).
        """
        credentials_ref: str | None = None

        if credential:
            from datapulse.control_center.credentials import store_credential  # noqa: PLC0415

            cred_id = store_credential(
                self._session,
                connection_id=connection_id,
                tenant_id=tenant_id,
                cred_type="password",
                plain_value=credential,
            )
            credentials_ref = str(cred_id)

        row = self._connections.update(
            connection_id,
            name=name,
            status=status,
            config_json=config,
            credentials_ref=credentials_ref,
        )
        return SourceConnection(**row) if row else None

    def archive_connection(self, connection_id: int) -> bool:
        """Set the connection status to 'archived'.

        Returns True if found, False if the id does not exist.
        """
        return self._connections.archive(connection_id)

    def test_connection(
        self,
        connection_id: int,
        *,
        tenant_id: int,
    ) -> ConnectionTestResult:
        """Run a connectivity test for the given source connection.

        Delegates to the appropriate SourceConnector.  Returns
        ``ok=False`` when the connection is not found or the source type
        has no connector registered yet.
        """
        conn = self.get_connection(connection_id)
        if conn is None:
            return ConnectionTestResult(ok=False, error="connection_not_found")

        connector = _get_connector(
            conn.source_type,
            session=self._session,
            connection_id=conn.id,
            tenant_id=tenant_id,
        )
        if connector is None:
            return ConnectionTestResult(
                ok=False,
                error=f"test_not_supported_for_source_type:{conn.source_type}",
            )
        return connector.test(tenant_id=tenant_id, config=conn.config)

    def preview_connection(
        self,
        *,
        connection_id: int,
        tenant_id: int,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> ConnectionPreviewResult:
        """Return a read-only data sample for the given source connection.

        Raises:
            ValueError:        When the connection does not exist, or the
                               source type does not support preview.
            FileNotFoundError: When the underlying file is no longer available.
        """
        from datapulse.control_center import preview as preview_engine  # noqa: PLC0415

        conn = self.get_connection(connection_id)
        if conn is None:
            raise ValueError("connection_not_found")

        if conn.source_type == "file_upload":
            return preview_engine.preview_file_upload(
                tenant_id,
                conn.config,
                max_rows=max_rows,
                sample_rows=sample_rows,
            )

        # Delegate all other source types to their registered connector
        connector = _get_connector(conn.source_type)
        if connector is not None:
            return connector.preview(
                tenant_id=tenant_id,
                config=conn.config,
                max_rows=max_rows,
                sample_rows=sample_rows,
            )

        raise ValueError(f"preview_not_supported_for:{conn.source_type}")
