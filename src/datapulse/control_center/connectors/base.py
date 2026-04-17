"""SourceConnector protocol — implemented by every source type connector.

A connector knows how to:
  - ``test``   – verify the source is reachable and the config is valid.
  - ``preview``– read a sample of the source data without touching bronze.

New source types (google_sheets, postgres, …) add a class here that
implements this protocol.  No changes to service.py are needed — only a
new entry in ``service._CONNECTORS``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from datapulse.control_center.models import ConnectionPreviewResult, ConnectionTestResult


@runtime_checkable
class SourceConnector(Protocol):
    """Duck-typed contract for all data source connectors."""

    def test(self, *, tenant_id: int, config: dict) -> ConnectionTestResult:
        """Verify that the connection is reachable and the config is valid.

        Args:
            tenant_id: The current tenant (used to locate tenant-scoped files).
            config:    The ``config_json`` dict stored on SourceConnection.

        Returns:
            ConnectionTestResult with ``ok=True`` on success.
        """
        ...

    def preview(
        self,
        *,
        tenant_id: int,
        config: dict,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> ConnectionPreviewResult:
        """Read a data sample without writing to bronze.

        Args:
            tenant_id:   The current tenant.
            config:      The ``config_json`` dict stored on SourceConnection.
            max_rows:    Maximum rows to read from the source.
            sample_rows: Maximum rows to include in ``sample_rows`` output.

        Returns:
            ConnectionPreviewResult with column metadata and sample data.
        """
        ...
