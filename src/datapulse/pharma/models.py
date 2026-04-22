"""Pydantic models for the pharma drug-master and EDA reporting module."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DrugMasterEntry(BaseModel):
    """A single drug catalog entry (pharma.drug_master row)."""

    model_config = ConfigDict(frozen=True)

    ean13: str | None = None
    name_en: str
    name_ar: str | None = None
    strength: str | None = None
    form: str | None = None
    atc_code: str | None = None
    controlled_schedule: int = 0
    default_price_egp: Decimal | None = None
    active_ingredient: str | None = None
    is_active: bool = True


class DrugMasterSearchResult(DrugMasterEntry):
    """Drug catalog entry enriched with DB metadata returned from search queries."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime
    updated_at: datetime


class EDAExport(BaseModel):
    """A recorded EDA export event (pharma.eda_exports row)."""

    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    period_start: date | None = None
    period_end: date | None = None
    export_type: Literal["monthly", "controlled"]
    file_path: str | None = None
    file_sha256: str | None = None
    row_count: int | None = None
    created_at: datetime
    created_by: str | None = None


class EDAExportRequest(BaseModel):
    """Request body for generating a new EDA export."""

    model_config = ConfigDict(frozen=True)

    period_start: date
    period_end: date
    export_type: Literal["monthly", "controlled"]


class DrugMasterImportResult(BaseModel):
    """Summary returned after a bulk drug-master import."""

    model_config = ConfigDict(frozen=True)

    rows_imported: int
    rows_skipped: int
