"""Tests for expiry Pydantic models — validation and immutability."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from datapulse.expiry.models import (
    BatchInfo,
    ExpiryAlert,
    ExpiryCalendarDay,
    ExpiryFilter,
    ExpirySummary,
    FefoRequest,
    FefoResponse,
    QuarantineRequest,
    WriteOffRequest,
)

# ------------------------------------------------------------------
# BatchInfo
# ------------------------------------------------------------------


def test_batch_info_creation():
    b = BatchInfo(
        batch_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        batch_number="B001",
        expiry_date=date(2025, 6, 1),
        current_quantity=Decimal("100"),
        days_to_expiry=45,
        alert_level="warning",
        computed_status="near_expiry",
    )
    assert b.drug_code == "D001"
    assert b.alert_level == "warning"
    assert b.days_to_expiry == 45


def test_batch_info_frozen():
    b = BatchInfo(
        batch_key=1,
        drug_code="D001",
        drug_name="Drug",
        site_code="S01",
        batch_number="B001",
        expiry_date=date(2025, 6, 1),
        current_quantity=Decimal("100"),
        days_to_expiry=45,
        alert_level="warning",
        computed_status="near_expiry",
    )
    with pytest.raises(ValidationError):
        b.drug_code = "D999"


# ------------------------------------------------------------------
# ExpiryAlert
# ------------------------------------------------------------------


def test_expiry_alert_creation():
    a = ExpiryAlert(
        drug_code="D001",
        drug_name="Paracetamol",
        batch_number="B001",
        site_code="S01",
        expiry_date=date(2025, 6, 1),
        current_quantity=Decimal("50"),
        days_to_expiry=15,
        alert_level="critical",
    )
    assert a.alert_level == "critical"
    assert a.drug_brand is None


def test_expiry_alert_with_brand():
    a = ExpiryAlert(
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Panadol",
        batch_number="B001",
        site_code="S01",
        expiry_date=date(2025, 6, 1),
        current_quantity=Decimal("50"),
        days_to_expiry=15,
        alert_level="critical",
    )
    assert a.drug_brand == "Panadol"


def test_expiry_alert_frozen():
    a = ExpiryAlert(
        drug_code="D001",
        drug_name="Drug",
        batch_number="B001",
        site_code="S01",
        expiry_date=date(2025, 6, 1),
        current_quantity=Decimal("10"),
        days_to_expiry=10,
        alert_level="critical",
    )
    with pytest.raises(ValidationError):
        a.drug_code = "X"


# ------------------------------------------------------------------
# ExpirySummary
# ------------------------------------------------------------------


def test_expiry_summary_creation():
    s = ExpirySummary(
        site_key=1,
        site_code="S01",
        site_name="Main",
        expiry_bucket="expired",
        batch_count=5,
        total_quantity=Decimal("50"),
        total_value=Decimal("250"),
    )
    assert s.batch_count == 5
    assert s.expiry_bucket == "expired"


def test_expiry_summary_frozen():
    s = ExpirySummary(
        site_key=1,
        site_code="S01",
        site_name="Main",
        expiry_bucket="active",
        batch_count=10,
        total_quantity=Decimal("100"),
        total_value=Decimal("500"),
    )
    with pytest.raises(ValidationError):
        s.batch_count = 99


# ------------------------------------------------------------------
# ExpiryCalendarDay
# ------------------------------------------------------------------


def test_expiry_calendar_day_creation():
    d = ExpiryCalendarDay(
        expiry_date=date(2025, 6, 1),
        batch_count=3,
        total_quantity=Decimal("30"),
        alert_level="warning",
    )
    assert d.batch_count == 3
    assert d.alert_level == "warning"


# ------------------------------------------------------------------
# ExpiryFilter
# ------------------------------------------------------------------


def test_expiry_filter_defaults():
    f = ExpiryFilter()
    assert f.limit == 100
    assert f.days_threshold == 90
    assert f.site_code is None
    assert f.drug_code is None
    assert f.alert_level is None


def test_expiry_filter_limit_bounds():
    with pytest.raises(ValidationError):
        ExpiryFilter(limit=0)
    with pytest.raises(ValidationError):
        ExpiryFilter(limit=501)


def test_expiry_filter_days_threshold_bounds():
    with pytest.raises(ValidationError):
        ExpiryFilter(days_threshold=0)
    with pytest.raises(ValidationError):
        ExpiryFilter(days_threshold=366)


def test_expiry_filter_frozen():
    f = ExpiryFilter(limit=50)
    with pytest.raises(ValidationError):
        f.limit = 100


# ------------------------------------------------------------------
# QuarantineRequest
# ------------------------------------------------------------------


def test_quarantine_request_creation():
    q = QuarantineRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Contamination suspected",
    )
    assert q.drug_code == "D001"
    assert q.reason == "Contamination suspected"


def test_quarantine_request_drug_code_max_length():
    with pytest.raises(ValidationError):
        QuarantineRequest(
            drug_code="x" * 101,
            site_code="S01",
            batch_number="B001",
            reason="Test",
        )


def test_quarantine_request_reason_max_length():
    with pytest.raises(ValidationError):
        QuarantineRequest(
            drug_code="D001",
            site_code="S01",
            batch_number="B001",
            reason="x" * 501,
        )


def test_quarantine_request_frozen():
    q = QuarantineRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Test",
    )
    with pytest.raises(ValidationError):
        q.drug_code = "D999"


# ------------------------------------------------------------------
# WriteOffRequest
# ------------------------------------------------------------------


def test_write_off_request_creation():
    w = WriteOffRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Past expiry",
        quantity=Decimal("10"),
    )
    assert w.quantity == Decimal("10")
    assert w.reason == "Past expiry"


def test_write_off_request_frozen():
    w = WriteOffRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Test",
        quantity=Decimal("5"),
    )
    with pytest.raises(ValidationError):
        w.quantity = Decimal("999")


# ------------------------------------------------------------------
# FefoRequest / FefoResponse
# ------------------------------------------------------------------


def test_fefo_request_creation():
    r = FefoRequest(
        drug_code="D001",
        site_code="S01",
        required_quantity=Decimal("50"),
    )
    assert r.required_quantity == Decimal("50")


def test_fefo_response_creation():
    resp = FefoResponse(
        drug_code="D001",
        site_code="S01",
        required_quantity=Decimal("50"),
        fulfilled=True,
        remaining_unfulfilled=Decimal("0"),
        selections=[],
    )
    assert resp.fulfilled is True
    assert resp.remaining_unfulfilled == Decimal("0")
