"""Unit tests for rx and insurance Pydantic models (issues #605).

Simple instantiation + validation tests — no DB required.
Covers rx/models.py and insurance/models.py to satisfy coverage gates.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from datapulse.insurance.models import (
    Claim,
    ClaimBase,
    ClaimItem,
    ClaimItemBase,
    ClaimItemCreate,
    InsuranceCompany,
    InsuranceCompanyBase,
    InsurancePlan,
    InsurancePlanBase,
)
from datapulse.rx.models import (
    DispenseEvent,
    DispenseEventBase,
    DispenseEventCreate,
    Prescription,
    PrescriptionBase,
    PrescriptionCreate,
    PrescriptionItem,
    PrescriptionItemBase,
    PrescriptionItemCreate,
)

NOW = datetime(2026, 4, 23, 12, 0, 0)
TODAY = date(2026, 4, 23)


# ── Insurance models ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_insurance_company_base():
    c = InsuranceCompanyBase(tenant_id=1, name="AllianzEG", code="ALZ")
    assert c.name == "AllianzEG"
    assert c.is_active is True


@pytest.mark.unit
def test_insurance_company_full():
    c = InsuranceCompany(
        id=5,
        tenant_id=1,
        name="AllianzEG",
        code="ALZ",
        created_at=NOW,
    )
    assert c.id == 5
    assert c.created_at == NOW


@pytest.mark.unit
def test_insurance_plan_base():
    p = InsurancePlanBase(company_id=1, name="Silver", copay_pct=Decimal("20.00"))
    assert p.copay_pct == Decimal("20.00")
    assert p.is_active is True


@pytest.mark.unit
def test_insurance_plan_full():
    p = InsurancePlan(
        id=10,
        company_id=1,
        name="Silver",
        copay_pct=Decimal("20.00"),
    )
    assert p.id == 10


@pytest.mark.unit
def test_claim_base_defaults():
    c = ClaimBase(tenant_id=1)
    assert c.status == "draft"
    assert c.total_egp is None


@pytest.mark.unit
def test_claim_full():
    c = Claim(
        id=99,
        tenant_id=1,
        status="approved",
        total_egp=Decimal("500.00"),
        copay_egp=Decimal("100.00"),
        insurance_due_egp=Decimal("400.00"),
        created_at=NOW,
    )
    assert c.id == 99
    assert c.status == "approved"


@pytest.mark.unit
def test_claim_item_base():
    ci = ClaimItemBase(claim_id=99, drug_code="AMX500", quantity=Decimal("2"))
    assert ci.drug_code == "AMX500"


@pytest.mark.unit
def test_claim_item_create():
    ci = ClaimItemCreate(
        claim_id=1, drug_code="IBU400", quantity=Decimal("1"), unit_price=Decimal("25.50")
    )
    assert ci.unit_price == Decimal("25.50")


@pytest.mark.unit
def test_claim_item_full():
    ci = ClaimItem(id=7, claim_id=1, drug_code="IBU400")
    assert ci.id == 7


# ── Rx models ────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_prescription_base_defaults():
    p = PrescriptionBase(tenant_id=1, issue_date=TODAY)
    assert p.refills_total == 1
    assert p.refills_used == 0
    assert p.patient_name is None


@pytest.mark.unit
def test_prescription_full():
    p = Prescription(
        id=42,
        tenant_id=1,
        issue_date=TODAY,
        doctor_name="Dr. Salah",
        created_at=NOW,
    )
    assert p.id == 42
    assert p.doctor_name == "Dr. Salah"


@pytest.mark.unit
def test_prescription_create():
    pc = PrescriptionCreate(tenant_id=1, issue_date=TODAY, refills_total=3)
    assert pc.refills_total == 3


@pytest.mark.unit
def test_prescription_item_base():
    pi = PrescriptionItemBase(prescription_id=42, drug_code="AMX500", quantity=Decimal("1.5"))
    assert pi.drug_code == "AMX500"
    assert pi.quantity == Decimal("1.5")


@pytest.mark.unit
def test_prescription_item_create():
    pi = PrescriptionItemCreate(
        prescription_id=1, drug_code="VIT_C", quantity=Decimal("2"), instructions="مرتين يومياً"
    )
    assert pi.instructions == "مرتين يومياً"


@pytest.mark.unit
def test_prescription_item_full():
    pi = PrescriptionItem(id=11, prescription_id=1, drug_code="PARA")
    assert pi.id == 11


@pytest.mark.unit
def test_dispense_event_base():
    de = DispenseEventBase(prescription_id=42, dispensed_by="cashier-01")
    assert de.dispensed_by == "cashier-01"
    assert de.transaction_id is None


@pytest.mark.unit
def test_dispense_event_create():
    de = DispenseEventCreate(prescription_id=42, dispensed_by="ph-01", transaction_id=100)
    assert de.transaction_id == 100


@pytest.mark.unit
def test_dispense_event_full():
    de = DispenseEvent(id=5, prescription_id=42, dispensed_by="ph-01", dispensed_at=NOW)
    assert de.id == 5
    assert de.dispensed_at == NOW
