"""Pydantic models for the insurance claims module.

Mirrors:
    insurance.insurance_companies  — insurer records per tenant
    insurance.insurance_plans      — plan definitions per company
    insurance.claims               — claim headers
    insurance.claim_items          — line items per claim

See migration 108_insurance_claims.sql for the DB schema.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ── Insurance Companies ────────────────────────────────────────────────────


class InsuranceCompanyBase(BaseModel):
    """Fields shared between create and read models."""

    model_config = ConfigDict(frozen=True)

    tenant_id: int
    name: str
    code: str | None = None
    contact_email: str | None = None
    is_active: bool = True


class InsuranceCompany(InsuranceCompanyBase):
    """A full insurance company record as stored in the DB."""

    id: int
    created_at: datetime


class InsuranceCompanyCreate(BaseModel):
    """Request body for creating a new insurance company."""

    model_config = ConfigDict(frozen=True)

    name: str
    code: str | None = None
    contact_email: str | None = None
    is_active: bool = True


# ── Insurance Plans ────────────────────────────────────────────────────────


class InsurancePlanBase(BaseModel):
    """Fields shared between create and read models for insurance plans."""

    model_config = ConfigDict(frozen=True)

    company_id: int
    name: str | None = None
    copay_pct: Decimal = Decimal("0.00")
    plan_code: str | None = None
    is_active: bool = True


class InsurancePlan(InsurancePlanBase):
    """A full insurance plan record as stored in the DB."""

    id: int


class InsurancePlanCreate(BaseModel):
    """Request body for creating a new insurance plan."""

    model_config = ConfigDict(frozen=True)

    company_id: int
    name: str | None = None
    copay_pct: Decimal = Decimal("0.00")
    plan_code: str | None = None
    is_active: bool = True


# ── Claims ─────────────────────────────────────────────────────────────────

ClaimStatus = Literal["draft", "submitted", "approved", "rejected", "paid"]


class ClaimBase(BaseModel):
    """Shared claim header fields."""

    model_config = ConfigDict(frozen=True)

    tenant_id: int
    transaction_id: int | None = None
    plan_id: int | None = None
    patient_name: str | None = None
    patient_id_no: str | None = None
    total_egp: Decimal | None = None
    copay_egp: Decimal | None = None
    insurance_due_egp: Decimal | None = None
    status: ClaimStatus = "draft"
    submitted_at: datetime | None = None
    approved_at: datetime | None = None


class Claim(ClaimBase):
    """A full claim record as stored in the DB."""

    id: int
    created_at: datetime


class ClaimCreate(BaseModel):
    """Request body for creating a new insurance claim."""

    model_config = ConfigDict(frozen=True)

    transaction_id: int | None = None
    plan_id: int | None = None
    patient_name: str | None = None
    patient_id_no: str | None = None
    total_egp: Decimal | None = None
    copay_egp: Decimal | None = None
    insurance_due_egp: Decimal | None = None


# ── Claim Items ────────────────────────────────────────────────────────────


class ClaimItemBase(BaseModel):
    """Shared line-item fields."""

    model_config = ConfigDict(frozen=True)

    claim_id: int
    drug_code: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None


class ClaimItem(ClaimItemBase):
    """A full claim line-item record as stored in the DB."""

    id: int


class ClaimItemCreate(BaseModel):
    """Request body for adding a line item to a claim."""

    model_config = ConfigDict(frozen=True)

    drug_code: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None
