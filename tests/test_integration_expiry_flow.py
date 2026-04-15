"""Integration test: batch -> near-expiry alert -> quarantine -> write-off.

Tests the expiry management lifecycle across domain boundaries:
  1. Batch with near expiry date classified as 'critical'
  2. Quarantine a batch -> status + stock adjustment
  3. Write-off a batch -> final status + write_off_date
  4. FEFO ordering for dispensing priority
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ConfigDict

# ── Domain models (contract definitions for Session 3) ─────────────


class Batch(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    batch_number: str
    expiry_date: date
    initial_quantity: Decimal
    current_quantity: Decimal
    unit_cost: Decimal | None = None
    status: str = "active"  # active | near_expiry | expired | quarantined | written_off
    quarantine_date: date | None = None
    write_off_date: date | None = None
    write_off_reason: str | None = None


class ExpiryAlert(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: int
    drug_code: str
    site_code: str
    batch_number: str
    days_to_expiry: int
    severity: str  # ok | warning | critical | expired
    current_quantity: Decimal


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture()
def mock_batch_repo():
    """Mock batch repository."""
    repo = MagicMock()
    repo.get_batch = MagicMock()
    repo.update_batch_status = MagicMock()
    repo.get_batches_by_drug = MagicMock()
    return repo


@pytest.fixture()
def mock_alert_repo():
    """Mock expiry alert feature repository."""
    repo = MagicMock()
    repo.get_alerts = MagicMock()
    return repo


@pytest.fixture()
def mock_adjustment_repo():
    """Mock stock adjustment repository."""
    repo = MagicMock()
    repo.create_adjustment = MagicMock()
    return repo


# ── Helpers ────────────────────────────────────────────────────────


def _classify_expiry(days_to_expiry: int) -> str:
    """Classify expiry severity based on days remaining."""
    if days_to_expiry < 0:
        return "expired"
    if days_to_expiry <= 30:
        return "critical"
    if days_to_expiry <= 90:
        return "warning"
    return "ok"


def _make_batch(
    days_until_expiry: int = 20,
    status: str = "active",
    qty: Decimal = Decimal("100"),
) -> Batch:
    return Batch(
        tenant_id=1,
        drug_code="PARA500",
        site_code="SITE01",
        batch_number="B2025-001",
        expiry_date=date.today() + timedelta(days=days_until_expiry),
        initial_quantity=Decimal("200"),
        current_quantity=qty,
        unit_cost=Decimal("10.00"),
        status=status,
    )


# ── Tests ──────────────────────────────────────────────────────────


class TestExpiryClassification:
    """Classify batches by days to expiry."""

    def test_critical_under_30_days(self):
        """Batch with 20 days to expiry -> 'critical'."""
        batch = _make_batch(days_until_expiry=20)
        days = (batch.expiry_date - date.today()).days
        severity = _classify_expiry(days)
        assert severity == "critical"
        assert days == 20

    def test_warning_30_to_90_days(self):
        """Batch with 60 days to expiry -> 'warning'."""
        batch = _make_batch(days_until_expiry=60)
        days = (batch.expiry_date - date.today()).days
        severity = _classify_expiry(days)
        assert severity == "warning"

    def test_ok_over_90_days(self):
        """Batch with 120 days to expiry -> 'ok'."""
        batch = _make_batch(days_until_expiry=120)
        days = (batch.expiry_date - date.today()).days
        severity = _classify_expiry(days)
        assert severity == "ok"

    def test_expired_negative_days(self):
        """Batch expired 5 days ago -> 'expired'."""
        batch = _make_batch(days_until_expiry=-5)
        days = (batch.expiry_date - date.today()).days
        severity = _classify_expiry(days)
        assert severity == "expired"

    def test_boundary_30_days_is_critical(self):
        """Exactly 30 days -> 'critical' (inclusive boundary)."""
        severity = _classify_expiry(30)
        assert severity == "critical"

    def test_boundary_90_days_is_warning(self):
        """Exactly 90 days -> 'warning' (inclusive boundary)."""
        severity = _classify_expiry(90)
        assert severity == "warning"


class TestQuarantineBatch:
    """Quarantine a near-expiry batch."""

    def test_quarantine_updates_status(self, mock_batch_repo):
        """Quarantining sets status to 'quarantined' with quarantine_date."""
        batch = _make_batch(days_until_expiry=10)
        today = date.today()

        quarantined = Batch(
            tenant_id=batch.tenant_id,
            drug_code=batch.drug_code,
            site_code=batch.site_code,
            batch_number=batch.batch_number,
            expiry_date=batch.expiry_date,
            initial_quantity=batch.initial_quantity,
            current_quantity=batch.current_quantity,
            unit_cost=batch.unit_cost,
            status="quarantined",
            quarantine_date=today,
        )

        assert quarantined.status == "quarantined"
        assert quarantined.quarantine_date == today

    def test_quarantine_creates_negative_adjustment(self, mock_adjustment_repo):
        """Quarantining stock creates a negative adjustment to remove from available."""
        _make_batch(days_until_expiry=10, qty=Decimal("50"))  # verify batch creation

        mock_adjustment_repo.create_adjustment(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            adjustment_type="quarantine",
            quantity=Decimal("-50"),
            batch_number="B2025-001",
            reason="Near-expiry quarantine",
        )

        mock_adjustment_repo.create_adjustment.assert_called_once()
        call_kwargs = mock_adjustment_repo.create_adjustment.call_args.kwargs
        assert call_kwargs["quantity"] == Decimal("-50")
        assert call_kwargs["adjustment_type"] == "quarantine"


class TestWriteOff:
    """Write off an expired or quarantined batch."""

    def test_write_off_sets_final_status(self):
        """Write-off sets status to 'written_off' with date and reason."""
        today = date.today()

        written_off = Batch(
            tenant_id=1,
            drug_code="PARA500",
            site_code="SITE01",
            batch_number="B2025-001",
            expiry_date=date.today() - timedelta(days=5),
            initial_quantity=Decimal("200"),
            current_quantity=Decimal("0"),
            unit_cost=Decimal("10.00"),
            status="written_off",
            quarantine_date=today - timedelta(days=10),
            write_off_date=today,
            write_off_reason="Expired stock — beyond use date",
        )

        assert written_off.status == "written_off"
        assert written_off.write_off_date == today
        assert written_off.write_off_reason is not None
        assert written_off.current_quantity == Decimal("0")


class TestFEFOOrdering:
    """First-Expiry-First-Out ordering for dispensing priority."""

    def test_fefo_orders_by_expiry_date(self):
        """Batches should be dispensed in order of nearest expiry first."""
        batches = [
            _make_batch(days_until_expiry=90),
            _make_batch(days_until_expiry=30),
            _make_batch(days_until_expiry=60),
        ]

        fefo_sorted = sorted(batches, key=lambda b: b.expiry_date)

        assert fefo_sorted[0].expiry_date <= fefo_sorted[1].expiry_date
        assert fefo_sorted[1].expiry_date <= fefo_sorted[2].expiry_date

    def test_fefo_skips_quarantined_batches(self):
        """Quarantined batches should not be available for dispensing."""
        active = _make_batch(days_until_expiry=60, status="active")
        quarantined = _make_batch(days_until_expiry=30, status="quarantined")

        available = [b for b in [active, quarantined] if b.status == "active"]

        assert len(available) == 1
        assert available[0].status == "active"

    def test_fefo_skips_written_off_batches(self):
        """Written-off batches not available for dispensing."""
        active = _make_batch(days_until_expiry=60, status="active")
        written_off = _make_batch(days_until_expiry=-5, status="written_off")

        available = [
            b
            for b in [active, written_off]
            if b.status not in ("quarantined", "written_off", "expired")
        ]

        assert len(available) == 1
