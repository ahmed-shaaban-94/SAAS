"""Unit tests for the tenant-aggregate exposure-tier endpoint (#506).

Covers:
- Repository: day-band CASE → 30/60/90 tier mapping, always returns 3 rows.
- Service: cache-through behaviour (hit + miss paths).
- Idempotent fixed-order rows even when the DB returns a subset.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from datapulse.expiry.models import ExpiryExposureTier, ExpiryFilter
from datapulse.expiry.repository import ExpiryRepository
from datapulse.expiry.service import ExpiryService

# ────────────────────────────────────────────────────────────────────────
# Repository
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def repo(mock_session):
    return ExpiryRepository(mock_session)


def _mock_mapping_rows(mock_session, rows):
    """Wire the SQLAlchemy mappings().all() chain."""
    mock_session.execute.return_value.mappings.return_value.all.return_value = rows


def test_exposure_tiers_returns_three_rows_in_fixed_order(repo, mock_session):
    """30d → 60d → 90d order, regardless of DB GROUP BY order."""
    _mock_mapping_rows(
        mock_session,
        [
            {"tier": "90d", "batch_count": 3, "total_egp": Decimal("32000")},
            {"tier": "30d", "batch_count": 4, "total_egp": Decimal("48000")},
            {"tier": "60d", "batch_count": 5, "total_egp": Decimal("62000")},
        ],
    )

    result = repo.get_exposure_tiers(ExpiryFilter())

    assert [t.tier for t in result] == ["30d", "60d", "90d"]
    assert [t.label for t in result] == [
        "Within 30 days",
        "31-60 days",
        "61-90 days",
    ]
    assert [t.tone for t in result] == ["red", "amber", "green"]


def test_exposure_tiers_maps_totals_and_counts(repo, mock_session):
    _mock_mapping_rows(
        mock_session,
        [
            {"tier": "30d", "batch_count": 4, "total_egp": Decimal("48000")},
            {"tier": "60d", "batch_count": 5, "total_egp": Decimal("62000")},
            {"tier": "90d", "batch_count": 3, "total_egp": Decimal("32000")},
        ],
    )

    result = repo.get_exposure_tiers(ExpiryFilter())

    by_tier = {t.tier: t for t in result}
    assert by_tier["30d"].total_egp == Decimal("48000")
    assert by_tier["30d"].batch_count == 4
    assert by_tier["60d"].total_egp == Decimal("62000")
    assert by_tier["60d"].batch_count == 5
    assert by_tier["90d"].total_egp == Decimal("32000")
    assert by_tier["90d"].batch_count == 3


def test_exposure_tiers_fills_missing_tiers_with_zero(repo, mock_session):
    """Tenants with no near-expiry inventory still get 3 rows — all zero."""
    _mock_mapping_rows(mock_session, [])

    result = repo.get_exposure_tiers(ExpiryFilter())

    assert len(result) == 3
    assert all(t.total_egp == Decimal("0") for t in result)
    assert all(t.batch_count == 0 for t in result)


def test_exposure_tiers_partial_data_zero_fills(repo, mock_session):
    """Only 30d tier has batches → 60d/90d appear with zeros."""
    _mock_mapping_rows(
        mock_session,
        [
            {"tier": "30d", "batch_count": 2, "total_egp": Decimal("15000")},
        ],
    )

    result = repo.get_exposure_tiers(ExpiryFilter())

    by_tier = {t.tier: t for t in result}
    assert by_tier["30d"].total_egp == Decimal("15000")
    assert by_tier["60d"].total_egp == Decimal("0")
    assert by_tier["60d"].batch_count == 0
    assert by_tier["90d"].total_egp == Decimal("0")
    assert by_tier["90d"].batch_count == 0


def test_exposure_tiers_passes_site_filter(repo, mock_session):
    """site_code filter must be bound as a parameter (not interpolated)."""
    _mock_mapping_rows(mock_session, [])

    repo.get_exposure_tiers(ExpiryFilter(site_code="S1"))

    _stmt, params = mock_session.execute.call_args[0]
    assert params == {"site_code": "S1"}


def test_exposure_tiers_omits_site_filter_when_none(repo, mock_session):
    _mock_mapping_rows(mock_session, [])

    repo.get_exposure_tiers(ExpiryFilter())

    _stmt, params = mock_session.execute.call_args[0]
    assert params == {}


# ────────────────────────────────────────────────────────────────────────
# Service (cache behaviour)
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_repo() -> MagicMock:
    return create_autospec(ExpiryRepository, instance=True)


@pytest.fixture
def service(mock_repo: MagicMock) -> ExpiryService:
    return ExpiryService(mock_repo)


def _sample_tiers() -> list[ExpiryExposureTier]:
    return [
        ExpiryExposureTier(
            tier="30d",
            label="Within 30 days",
            total_egp=Decimal("48000"),
            batch_count=4,
            tone="red",
        ),
        ExpiryExposureTier(
            tier="60d",
            label="31-60 days",
            total_egp=Decimal("62000"),
            batch_count=5,
            tone="amber",
        ),
        ExpiryExposureTier(
            tier="90d",
            label="61-90 days",
            total_egp=Decimal("32000"),
            batch_count=3,
            tone="green",
        ),
    ]


def test_service_fetches_and_caches_on_miss(service: ExpiryService, mock_repo: MagicMock):
    tiers = _sample_tiers()
    mock_repo.get_exposure_tiers.return_value = tiers
    with (
        patch("datapulse.expiry.service.cache_get", return_value=None),
        patch("datapulse.expiry.service.cache_set") as cset,
    ):
        result = service.get_exposure_tiers(ExpiryFilter())

    mock_repo.get_exposure_tiers.assert_called_once()
    cset.assert_called_once()
    assert result == tiers


def test_service_returns_cached_and_skips_repo(service: ExpiryService, mock_repo: MagicMock):
    sentinel = _sample_tiers()
    with patch("datapulse.expiry.service.cache_get", return_value=sentinel):
        result = service.get_exposure_tiers(ExpiryFilter())

    mock_repo.get_exposure_tiers.assert_not_called()
    assert result is sentinel
