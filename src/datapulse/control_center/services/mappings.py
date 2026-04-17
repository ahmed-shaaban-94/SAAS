"""MappingsService — column mapping templates and standalone validation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from datapulse.control_center.models import (
    MappingTemplate,
    MappingTemplateList,
    ValidationReport,
)
from datapulse.control_center.repository import MappingTemplateRepository
from datapulse.logging import get_logger

log = get_logger(__name__)


class MappingsService:
    """Mapping template CRUD and standalone validation."""

    def __init__(self, session: Session, *, mappings: MappingTemplateRepository) -> None:
        self._session = session
        self._mappings = mappings

    # ── Mapping template reads ───────────────────────────────────────────────

    def list_mappings(
        self,
        *,
        source_type: str | None = None,
        template_name: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> MappingTemplateList:
        rows, total = self._mappings.list(
            source_type=source_type,
            template_name=template_name,
            page=page,
            page_size=page_size,
        )
        return MappingTemplateList(
            items=[MappingTemplate(**r) for r in rows],
            total=total,
        )

    def get_mapping(self, template_id: int) -> MappingTemplate | None:
        row = self._mappings.get(template_id)
        return MappingTemplate(**row) if row else None

    # ── Mapping template writes ──────────────────────────────────────────────

    def create_mapping(
        self,
        *,
        tenant_id: int,
        source_type: str,
        template_name: str,
        columns: list[dict[str, Any]],
        source_schema_hash: str | None = None,
        created_by: str | None = None,
    ) -> MappingTemplate:
        mapping_json = {"columns": columns}
        row = self._mappings.create(
            tenant_id=tenant_id,
            source_type=source_type,
            template_name=template_name,
            mapping_json=mapping_json,
            source_schema_hash=source_schema_hash,
            created_by=created_by,
        )
        return MappingTemplate(**row)

    def update_mapping(
        self,
        template_id: int,
        *,
        template_name: str | None = None,
        columns: list[dict[str, Any]] | None = None,
    ) -> MappingTemplate | None:
        mapping_json: dict[str, Any] | None = None
        if columns is not None:
            mapping_json = {"columns": columns}
        row = self._mappings.update(
            template_id,
            template_name=template_name,
            mapping_json=mapping_json,
        )
        return MappingTemplate(**row) if row else None

    def validate_mapping_standalone(
        self,
        *,
        columns: list[dict[str, Any]],
        target_domain: str,
        profile_config: dict[str, Any],
        source_preview: dict[str, Any] | None = None,
        tenant_id: int,
    ) -> ValidationReport:
        """Run the validation engine without persisting anything.

        Used by ``POST /mappings/validate`` for live feedback in the UI.
        """
        import datapulse.control_center.validation as val_engine  # noqa: PLC0415
        from datapulse.control_center import canonical as can_helpers  # noqa: PLC0415

        canonical = can_helpers.get_canonical_domain(self._session, target_domain)
        if canonical is None:
            from datapulse.control_center.models import ValidationIssue  # noqa: PLC0415

            return ValidationReport(
                ok=False,
                errors=[
                    ValidationIssue(
                        code="UNKNOWN_DOMAIN",
                        message=f"Canonical domain '{target_domain}' not found",
                        field="target_domain",
                    )
                ],
            )
        return val_engine.validate_draft(
            mapping_columns=columns,
            profile_config=profile_config,
            canonical_schema=canonical.get("json_schema", {}),
            source_preview=source_preview,
            tenant_id=tenant_id,
        )
