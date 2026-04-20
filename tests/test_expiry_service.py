"""Tests for ExpiryService — mock repository, verify caching and business logic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from datapulse.expiry.models import (
    ExpiryFilter,
    FefoRequest,
    QuarantineRequest,
    WriteOffRequest,
)
from datapulse.expiry.repository import ExpiryRepository
from datapulse.expiry.service import ExpiryService


@pytest.fixture()
def mock_repo() -> MagicMock:
    return create_autospec(ExpiryRepository, instance=True)


@pytest.fixture()
def service(mock_repo: MagicMock) -> ExpiryService:
    return ExpiryService(mock_repo)


# ------------------------------------------------------------------
# get_batches
# ------------------------------------------------------------------


def test_get_batches_calls_repo(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_batches.return_value = []
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set"),
    ):
        result = service.get_batches(ExpiryFilter())
    mock_repo.get_batches.assert_called_once()
    assert result == []


def test_get_batches_returns_cached(service: ExpiryService, mock_repo: MagicMock):
    sentinel = [object()]
    with patch("datapulse.expiry.service.cache_get", return_value=sentinel):
        result = service.get_batches(ExpiryFilter())
    mock_repo.get_batches.assert_not_called()
    assert result is sentinel


# ------------------------------------------------------------------
# get_near_expiry
# ------------------------------------------------------------------


def test_get_near_expiry_calls_repo(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_near_expiry.return_value = []
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set"),
    ):
        service.get_near_expiry(30, ExpiryFilter())
    mock_repo.get_near_expiry.assert_called_once_with(30, ExpiryFilter())


def test_get_near_expiry_caches_result(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_near_expiry.return_value = []
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set") as mock_set,
    ):
        service.get_near_expiry(30, ExpiryFilter())
    mock_set.assert_called_once()


# ------------------------------------------------------------------
# get_expired
# ------------------------------------------------------------------


def test_get_expired_calls_repo(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_expired.return_value = []
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set"),
    ):
        service.get_expired(ExpiryFilter())
    mock_repo.get_expired.assert_called_once()


# ------------------------------------------------------------------
# get_expiry_summary
# ------------------------------------------------------------------


def test_get_expiry_summary_calls_repo(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_expiry_summary.return_value = []
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set"),
    ):
        service.get_expiry_summary(ExpiryFilter())
    mock_repo.get_expiry_summary.assert_called_once()


# ------------------------------------------------------------------
# get_exposure_tiers (issue #506)
# ------------------------------------------------------------------


def test_get_exposure_tiers_calls_repo(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_exposure_tiers.return_value = []
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set"),
    ):
        service.get_exposure_tiers(ExpiryFilter())
    mock_repo.get_exposure_tiers.assert_called_once()


def test_get_exposure_tiers_returns_cached(service: ExpiryService, mock_repo: MagicMock):
    sentinel = [object()]
    with patch("datapulse.expiry.service.cache_get", return_value=sentinel):
        result = service.get_exposure_tiers(ExpiryFilter())
    mock_repo.get_exposure_tiers.assert_not_called()
    assert result is sentinel


def test_get_exposure_tiers_caches_result(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_exposure_tiers.return_value = []
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set") as mock_set,
    ):
        service.get_exposure_tiers(ExpiryFilter(site_code="S1"))
    mock_set.assert_called_once()


# ------------------------------------------------------------------
# get_expiry_calendar
# ------------------------------------------------------------------


def test_get_expiry_calendar_calls_repo(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_expiry_calendar.return_value = []
    start = date(2025, 1, 1)
    end = date(2025, 3, 31)
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set"),
    ):
        service.get_expiry_calendar(start, end, ExpiryFilter())
    mock_repo.get_expiry_calendar.assert_called_once_with(start, end, ExpiryFilter())


# ------------------------------------------------------------------
# select_fefo — FEFO integration via service
# ------------------------------------------------------------------


def test_select_fefo_returns_response(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_active_batches_for_fefo.return_value = [
        {
            "batch_number": "B001",
            "expiry_date": date(2025, 6, 1),
            "current_quantity": "100",
        }
    ]
    req = FefoRequest(drug_code="D001", site_code="S01", required_quantity=Decimal("50"))
    resp = service.select_fefo(req)
    assert resp.fulfilled is True
    assert resp.remaining_unfulfilled == Decimal("0")
    assert len(resp.selections) == 1
    assert resp.selections[0]["batch_number"] == "B001"


def test_select_fefo_partial_fulfillment(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_active_batches_for_fefo.return_value = [
        {
            "batch_number": "B001",
            "expiry_date": date(2025, 6, 1),
            "current_quantity": "30",
        }
    ]
    req = FefoRequest(drug_code="D001", site_code="S01", required_quantity=Decimal("100"))
    resp = service.select_fefo(req)
    assert resp.fulfilled is False
    assert float(resp.remaining_unfulfilled) == pytest.approx(70.0)


def test_select_fefo_no_stock(service: ExpiryService, mock_repo: MagicMock):
    mock_repo.get_active_batches_for_fefo.return_value = []
    req = FefoRequest(drug_code="D001", site_code="S01", required_quantity=Decimal("50"))
    resp = service.select_fefo(req)
    assert resp.fulfilled is False
    assert resp.selections == []


# ------------------------------------------------------------------
# quarantine_batch
# ------------------------------------------------------------------


def test_quarantine_batch_calls_repo(service: ExpiryService, mock_repo: MagicMock):
    req = QuarantineRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Test",
    )
    service.quarantine_batch(1, req)
    mock_repo.quarantine_batch.assert_called_once_with(1, req)


# ------------------------------------------------------------------
# write_off_batch
# ------------------------------------------------------------------


def test_write_off_batch_calls_repo(service: ExpiryService, mock_repo: MagicMock):
    req = WriteOffRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Expired",
        quantity=Decimal("10"),
    )
    service.write_off_batch(1, req)
    mock_repo.write_off_batch.assert_called_once_with(1, req)
