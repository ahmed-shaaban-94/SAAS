"""Tests for ExpiryRepository — mock SQLAlchemy session, verify SQL behavior."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.expiry.models import ExpiryFilter, QuarantineRequest, WriteOffRequest
from datapulse.expiry.repository import ExpiryRepository


@pytest.fixture()
def mock_session() -> MagicMock:
    session = MagicMock()
    # Default: .execute().mappings().all() returns []
    session.execute.return_value.mappings.return_value.all.return_value = []
    return session


@pytest.fixture()
def repo(mock_session: MagicMock) -> ExpiryRepository:
    return ExpiryRepository(mock_session)


# ------------------------------------------------------------------
# get_batches
# ------------------------------------------------------------------


def test_get_batches_calls_execute(repo: ExpiryRepository, mock_session: MagicMock):
    result = repo.get_batches(ExpiryFilter())
    mock_session.execute.assert_called_once()
    assert result == []


def test_get_batches_by_drug_passes_drug_code(repo: ExpiryRepository, mock_session: MagicMock):
    repo.get_batches_by_drug("D001", ExpiryFilter())
    # Drug code filter propagated — execute called with params containing drug_code
    _, kwargs = mock_session.execute.call_args
    params = mock_session.execute.call_args[0][1]
    assert params.get("drug_code") == "D001"


# ------------------------------------------------------------------
# get_near_expiry
# ------------------------------------------------------------------


def test_get_near_expiry_calls_execute(repo: ExpiryRepository, mock_session: MagicMock):
    result = repo.get_near_expiry(30, ExpiryFilter())
    mock_session.execute.assert_called_once()
    assert result == []


def test_get_near_expiry_passes_threshold(repo: ExpiryRepository, mock_session: MagicMock):
    repo.get_near_expiry(60, ExpiryFilter())
    params = mock_session.execute.call_args[0][1]
    assert params["days_threshold"] == 60


# ------------------------------------------------------------------
# get_expired
# ------------------------------------------------------------------


def test_get_expired_calls_execute(repo: ExpiryRepository, mock_session: MagicMock):
    result = repo.get_expired(ExpiryFilter())
    mock_session.execute.assert_called_once()
    assert result == []


# ------------------------------------------------------------------
# get_expiry_summary
# ------------------------------------------------------------------


def test_get_expiry_summary_calls_execute(repo: ExpiryRepository, mock_session: MagicMock):
    result = repo.get_expiry_summary(ExpiryFilter())
    mock_session.execute.assert_called_once()
    assert result == []


def test_get_expiry_summary_with_site_filter(repo: ExpiryRepository, mock_session: MagicMock):
    repo.get_expiry_summary(ExpiryFilter(site_code="S01"))
    params = mock_session.execute.call_args[0][1]
    assert params.get("site_code") == "S01"


# ------------------------------------------------------------------
# get_expiry_calendar
# ------------------------------------------------------------------


def test_get_expiry_calendar_calls_execute(repo: ExpiryRepository, mock_session: MagicMock):
    start = date(2025, 1, 1)
    end = date(2025, 3, 31)
    result = repo.get_expiry_calendar(start, end, ExpiryFilter())
    mock_session.execute.assert_called_once()
    params = mock_session.execute.call_args[0][1]
    assert params["start_date"] == start
    assert params["end_date"] == end
    assert result == []


# ------------------------------------------------------------------
# get_active_batches_for_fefo
# ------------------------------------------------------------------


def test_get_active_batches_for_fefo_calls_execute(repo: ExpiryRepository, mock_session: MagicMock):
    mock_session.execute.return_value.mappings.return_value.all.return_value = []
    result = repo.get_active_batches_for_fefo("D001", "S01")
    mock_session.execute.assert_called_once()
    params = mock_session.execute.call_args[0][1]
    assert params["drug_code"] == "D001"
    assert params["site_code"] == "S01"
    assert result == []


# ------------------------------------------------------------------
# quarantine_batch
# ------------------------------------------------------------------


def test_quarantine_batch_executes_update(repo: ExpiryRepository, mock_session: MagicMock):
    req = QuarantineRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Test quarantine",
    )
    repo.quarantine_batch(tenant_id=1, request=req)
    # UPDATE + INSERT (adjustment) = 2 execute calls
    assert mock_session.execute.call_count == 2


def test_quarantine_batch_passes_correct_params(repo: ExpiryRepository, mock_session: MagicMock):
    req = QuarantineRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Test",
    )
    repo.quarantine_batch(tenant_id=1, request=req)
    # First call = UPDATE
    first_params = mock_session.execute.call_args_list[0][0][1]
    assert first_params["drug_code"] == "D001"
    assert first_params["batch_number"] == "B001"
    assert first_params["tenant_id"] == 1


# ------------------------------------------------------------------
# write_off_batch
# ------------------------------------------------------------------


def test_write_off_batch_executes_update(repo: ExpiryRepository, mock_session: MagicMock):
    req = WriteOffRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Expired",
        quantity=Decimal("10"),
    )
    repo.write_off_batch(tenant_id=1, request=req)
    # UPDATE + INSERT = 2 execute calls
    assert mock_session.execute.call_count == 2


def test_write_off_batch_passes_quantity(repo: ExpiryRepository, mock_session: MagicMock):
    req = WriteOffRequest(
        drug_code="D001",
        site_code="S01",
        batch_number="B001",
        reason="Expired",
        quantity=Decimal("25"),
    )
    repo.write_off_batch(tenant_id=1, request=req)
    first_params = mock_session.execute.call_args_list[0][0][1]
    assert first_params["quantity"] == pytest.approx(25.0)
