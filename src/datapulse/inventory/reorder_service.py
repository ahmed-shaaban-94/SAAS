"""Reorder config service — business logic and validation."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from datapulse.core.exceptions import ValidationError
from datapulse.inventory.reorder_repository import ReorderConfig, ReorderConfigRepository
from datapulse.logging import get_logger

log = get_logger(__name__)


# ── Request / Response models ─────────────────────────────────────────────────


class ReorderConfigRequest(BaseModel):
    """Validated request body for create or update of a reorder config."""

    model_config = ConfigDict(frozen=True)

    drug_code: Annotated[str, Field(max_length=100)]
    site_code: Annotated[str, Field(max_length=100)]
    min_stock: Decimal = Field(ge=0)
    reorder_point: Decimal = Field(ge=0)
    max_stock: Decimal = Field(ge=0)
    reorder_lead_days: int = Field(default=7, ge=1, le=365)


class ReorderConfigResponse(BaseModel):
    """API response shape for a reorder config row."""

    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    drug_code: str
    site_code: str
    min_stock: Decimal
    reorder_point: Decimal
    max_stock: Decimal
    reorder_lead_days: int
    is_active: bool

    @classmethod
    def from_repo(cls, config: ReorderConfig) -> ReorderConfigResponse:
        return cls(
            id=config.id,
            tenant_id=config.tenant_id,
            drug_code=config.drug_code,
            site_code=config.site_code,
            min_stock=config.min_stock,
            reorder_point=config.reorder_point,
            max_stock=config.max_stock,
            reorder_lead_days=config.reorder_lead_days,
            is_active=config.is_active,
        )


# ── Service ───────────────────────────────────────────────────────────────────


class ReorderConfigService:
    """Business logic for reorder config CRUD.

    Enforces the invariant: min_stock <= reorder_point <= max_stock.
    """

    def __init__(self, repo: ReorderConfigRepository) -> None:
        self._repo = repo

    # ── Reads ─────────────────────────────────────────────────────────────────

    def get_config(
        self, tenant_id: int, drug_code: str, site_code: str
    ) -> ReorderConfigResponse | None:
        config = self._repo.get_config(tenant_id, drug_code, site_code)
        if config is None:
            return None
        return ReorderConfigResponse.from_repo(config)

    def list_configs(
        self,
        tenant_id: int,
        site_code: str | None = None,
        drug_code: str | None = None,
        is_active: bool | None = True,
        limit: int = 100,
    ) -> list[ReorderConfigResponse]:
        configs = self._repo.list_configs(
            tenant_id,
            site_code=site_code,
            drug_code=drug_code,
            is_active=is_active,
            limit=limit,
        )
        return [ReorderConfigResponse.from_repo(c) for c in configs]

    # ── Writes ────────────────────────────────────────────────────────────────

    def upsert_config(
        self,
        tenant_id: int,
        request: ReorderConfigRequest,
        updated_by: str | None = None,
    ) -> ReorderConfigResponse:
        """Create or update a reorder config, enforcing stock level constraints.

        Raises ValidationError if min_stock <= reorder_point <= max_stock is violated.
        """
        self._validate_thresholds(request.min_stock, request.reorder_point, request.max_stock)

        config = self._repo.upsert_config(
            tenant_id=tenant_id,
            drug_code=request.drug_code,
            site_code=request.site_code,
            min_stock=float(request.min_stock),
            reorder_point=float(request.reorder_point),
            max_stock=float(request.max_stock),
            reorder_lead_days=request.reorder_lead_days,
            updated_by=updated_by,
        )
        return ReorderConfigResponse.from_repo(config)

    def deactivate_config(self, tenant_id: int, drug_code: str, site_code: str) -> bool:
        """Soft-delete a reorder config. Returns False if not found."""
        return self._repo.deactivate_config(tenant_id, drug_code, site_code)

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_thresholds(
        min_stock: Decimal,
        reorder_point: Decimal,
        max_stock: Decimal,
    ) -> None:
        """Enforce min_stock <= reorder_point <= max_stock."""
        if min_stock > reorder_point:
            raise ValidationError(
                "min_stock must be less than or equal to reorder_point "
                f"(got min_stock={min_stock}, reorder_point={reorder_point})"
            )
        if reorder_point > max_stock:
            raise ValidationError(
                "reorder_point must be less than or equal to max_stock "
                f"(got reorder_point={reorder_point}, max_stock={max_stock})"
            )
