"""Pydantic models for the prescription (Rx) tracking module.

Mirrors:
    rx.prescriptions       — prescription headers
    rx.prescription_items  — drug line items per prescription
    rx.dispense_events     — dispensing audit trail

See migration 109_rx_tracking.sql for the DB schema.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# ── Prescriptions ──────────────────────────────────────────────────────────


class PrescriptionBase(BaseModel):
    """Fields shared between create and read models."""

    model_config = ConfigDict(frozen=True)

    tenant_id: int
    patient_name: str | None = None
    patient_dob: date | None = None
    doctor_name: str | None = None
    doctor_license: str | None = None
    issue_date: date
    expiry_date: date | None = None
    refills_total: int = 1
    refills_used: int = 0
    notes: str | None = None


class Prescription(PrescriptionBase):
    """A full prescription record as stored in the DB."""

    id: int
    created_at: datetime


class PrescriptionCreate(BaseModel):
    """Request body for creating a new prescription."""

    model_config = ConfigDict(frozen=True)

    patient_name: str | None = None
    patient_dob: date | None = None
    doctor_name: str | None = None
    doctor_license: str | None = None
    issue_date: date
    expiry_date: date | None = None
    refills_total: int = 1
    notes: str | None = None


# ── Prescription Items ─────────────────────────────────────────────────────


class PrescriptionItemBase(BaseModel):
    """Shared line-item fields."""

    model_config = ConfigDict(frozen=True)

    prescription_id: int
    drug_code: str
    quantity: Decimal | None = None
    instructions: str | None = None


class PrescriptionItem(PrescriptionItemBase):
    """A full prescription line-item record as stored in the DB."""

    id: int


class PrescriptionItemCreate(BaseModel):
    """Request body for adding a drug line item to a prescription."""

    model_config = ConfigDict(frozen=True)

    drug_code: str
    quantity: Decimal | None = None
    instructions: str | None = None


# ── Dispense Events ────────────────────────────────────────────────────────


class DispenseEventBase(BaseModel):
    """Shared dispense event fields."""

    model_config = ConfigDict(frozen=True)

    prescription_id: int
    transaction_id: int | None = None
    dispensed_by: str | None = None
    notes: str | None = None


class DispenseEvent(DispenseEventBase):
    """A full dispense event record as stored in the DB."""

    id: int
    dispensed_at: datetime


class DispenseEventCreate(BaseModel):
    """Request body for recording a new dispense event."""

    model_config = ConfigDict(frozen=True)

    prescription_id: int
    transaction_id: int | None = None
    dispensed_by: str | None = None
    notes: str | None = None
