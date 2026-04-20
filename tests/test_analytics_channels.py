"""Unit tests for the sales-channel breakdown (#505).

Covers:
- Repository: walk-in + insurance derivation, other-revenue folded back
  into retail, wholesale/online always emitted as zero-valued placeholders.
- Service: caching + default filter.
- Acceptance: fixed four-segment order, percentages sum to 100% when data
  exists, gracefully handles empty tenants.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from datapulse.analytics.breakdown_repository import BreakdownRepository
from datapulse.analytics.models import (
    AnalyticsFilter,
    ChannelsBreakdown,
    DateRange,
)
from datapulse.analytics.services.breakdown import BreakdownService

# ────────────────────────────────────────────────────────────────────────
# Repository
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def repo(mock_session):
    return BreakdownRepository(mock_session)


def _wire_row(mock_session, *, retail, institution, total):
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = {
        "retail_egp": Decimal(str(retail)),
        "institution_egp": Decimal(str(institution)),
        "total_egp": Decimal(str(total)),
    }


def _filters() -> AnalyticsFilter:
    return AnalyticsFilter(
        date_range=DateRange(start_date=date(2026, 4, 1), end_date=date(2026, 4, 20))
    )


def test_channels_breakdown_emits_four_fixed_segments(repo, mock_session):
    _wire_row(mock_session, retail=500, institution=200, total=1000)

    result = repo.get_channels_breakdown(_filters())

    assert [c.channel for c in result.items] == [
        "retail",
        "wholesale",
        "institution",
        "online",
    ]
    assert [c.label for c in result.items] == [
        "Retail walk-in",
        "Wholesale",
        "Institution",
        "Online",
    ]


def test_channels_breakdown_folds_other_revenue_into_retail(repo, mock_session):
    """total - retail - institution is fold-filled into retail so the
    donut sums to the tenant total without an 'unknown' bucket."""
    _wire_row(mock_session, retail=400, institution=200, total=1000)

    result = repo.get_channels_breakdown(_filters())

    by_channel = {c.channel: c for c in result.items}
    # 400 + (1000 - 400 - 200) = 800
    assert by_channel["retail"].value_egp == Decimal("800")
    assert by_channel["institution"].value_egp == Decimal("200")
    assert by_channel["wholesale"].value_egp == Decimal("0")
    assert by_channel["online"].value_egp == Decimal("0")


def test_channels_breakdown_percentages_sum_to_total(repo, mock_session):
    _wire_row(mock_session, retail=600, institution=200, total=1000)

    result = repo.get_channels_breakdown(_filters())

    # retail: 800 (fold-fill includes 200 other) → 80%
    # institution: 200 → 20%
    # wholesale/online: 0%
    by_channel = {c.channel: c for c in result.items}
    assert by_channel["retail"].pct_of_total == Decimal("80.00")
    assert by_channel["institution"].pct_of_total == Decimal("20.00")
    assert by_channel["wholesale"].pct_of_total == Decimal("0")
    assert by_channel["online"].pct_of_total == Decimal("0")


def test_channels_breakdown_unavailable_segments_tagged_source():
    """wholesale + online must be tagged ``source='unavailable'`` so the
    UI can show a tooltip explaining the gap."""
    session = MagicMock()
    _wire_row(session, retail=300, institution=100, total=500)
    repo = BreakdownRepository(session)

    result = repo.get_channels_breakdown(_filters())

    by_channel = {c.channel: c for c in result.items}
    assert by_channel["retail"].source == "derived"
    assert by_channel["institution"].source == "derived"
    assert by_channel["wholesale"].source == "unavailable"
    assert by_channel["online"].source == "unavailable"


def test_channels_breakdown_empty_tenant_returns_zeros(repo, mock_session):
    """No sales → all four segments still present, zero-valued."""
    _wire_row(mock_session, retail=0, institution=0, total=0)

    result = repo.get_channels_breakdown(_filters())

    assert result.total_egp == Decimal("0")
    for item in result.items:
        assert item.value_egp == Decimal("0")
        assert item.pct_of_total == Decimal("0")


def test_channels_breakdown_reports_partial_coverage(repo, mock_session):
    """Until wholesale + online ingestion lands, coverage stays 'partial'."""
    _wire_row(mock_session, retail=100, institution=50, total=150)

    result = repo.get_channels_breakdown(_filters())

    assert result.data_coverage == "partial"


def test_channels_breakdown_excludes_returns_from_sql(repo, mock_session):
    """The SQL must filter out ``is_return`` rows so refunds don't skew the donut."""
    _wire_row(mock_session, retail=100, institution=50, total=150)

    repo.get_channels_breakdown(_filters())

    rendered_sql = str(mock_session.execute.call_args[0][0])
    assert "NOT f.is_return" in rendered_sql


# ────────────────────────────────────────────────────────────────────────
# Service
# ────────────────────────────────────────────────────────────────────────


def _sample_breakdown() -> ChannelsBreakdown:
    from datapulse.analytics.models import ChannelShare

    return ChannelsBreakdown(
        items=[
            ChannelShare(
                channel="retail",
                label="Retail walk-in",
                value_egp=Decimal("800"),
                pct_of_total=Decimal("80"),
                source="derived",
            ),
            ChannelShare(
                channel="wholesale",
                label="Wholesale",
                value_egp=Decimal("0"),
                pct_of_total=Decimal("0"),
                source="unavailable",
            ),
            ChannelShare(
                channel="institution",
                label="Institution",
                value_egp=Decimal("200"),
                pct_of_total=Decimal("20"),
                source="derived",
            ),
            ChannelShare(
                channel="online",
                label="Online",
                value_egp=Decimal("0"),
                pct_of_total=Decimal("0"),
                source="unavailable",
            ),
        ],
        total_egp=Decimal("1000"),
        data_coverage="partial",
    )


def test_service_requires_breakdown_repo():
    """Service without a breakdown repo raises rather than silently returning
    stub data — same contract as the sibling breakdown methods."""
    analytics_repo = MagicMock()
    analytics_repo.get_data_date_range.return_value = (date(2026, 1, 1), date(2026, 4, 20))
    service = BreakdownService(repo=analytics_repo, breakdown_repo=None)

    with pytest.raises(RuntimeError, match="BreakdownRepository"):
        service.get_channels_breakdown()


def test_service_delegates_to_breakdown_repo():
    analytics_repo = MagicMock()
    analytics_repo.get_data_date_range.return_value = (date(2026, 1, 1), date(2026, 4, 20))
    breakdown_repo = create_autospec(BreakdownRepository, instance=True)
    breakdown_repo.get_channels_breakdown.return_value = _sample_breakdown()

    service = BreakdownService(repo=analytics_repo, breakdown_repo=breakdown_repo)

    with (
        patch("datapulse.cache_decorator.cache_get", return_value=None),
        patch("datapulse.cache_decorator.cache_set"),
    ):
        result = service.get_channels_breakdown(_filters())

    breakdown_repo.get_channels_breakdown.assert_called_once()
    assert result.items[0].channel == "retail"
    assert result.total_egp == Decimal("1000")


def test_service_defaults_to_trailing_30_days_when_filters_absent():
    """Unfiltered calls should populate a 30-day window ending at the
    latest data date — matches the sibling breakdowns' convention."""
    analytics_repo = MagicMock()
    analytics_repo.get_data_date_range.return_value = (date(2026, 1, 1), date(2026, 4, 20))
    breakdown_repo = create_autospec(BreakdownRepository, instance=True)
    breakdown_repo.get_channels_breakdown.return_value = _sample_breakdown()

    service = BreakdownService(repo=analytics_repo, breakdown_repo=breakdown_repo)

    with (
        patch("datapulse.cache_decorator.cache_get", return_value=None),
        patch("datapulse.cache_decorator.cache_set"),
    ):
        service.get_channels_breakdown()

    (filters_arg,) = breakdown_repo.get_channels_breakdown.call_args[0]
    assert filters_arg.date_range is not None
    assert filters_arg.date_range.end_date == date(2026, 4, 20)
    assert filters_arg.date_range.start_date == date(2026, 3, 21)
