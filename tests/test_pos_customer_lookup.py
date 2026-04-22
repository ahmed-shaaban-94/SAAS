"""Tests for POS phone-based customer lookup + per-customer churn (#624)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from datapulse.analytics.churn_repository import ChurnRepository
from datapulse.pos.customer_lookup_service import CustomerLookupService
from datapulse.pos.models.customer import PosCustomerLookup
from datapulse.pos.phone import normalize_egyptian_phone

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Phone normaliser — unit-testable without any DB
# ---------------------------------------------------------------------------


class TestNormalizeEgyptianPhone:
    def test_accepts_local_leading_zero(self) -> None:
        assert normalize_egyptian_phone("01198765432") == "+201198765432"

    def test_accepts_international_without_plus(self) -> None:
        assert normalize_egyptian_phone("201198765432") == "+201198765432"

    def test_accepts_canonical_e164(self) -> None:
        assert normalize_egyptian_phone("+201198765432") == "+201198765432"

    def test_accepts_00_prefix(self) -> None:
        assert normalize_egyptian_phone("00201198765432") == "+201198765432"

    def test_strips_whitespace_and_formatting(self) -> None:
        assert normalize_egyptian_phone("+20 (119) 876-5432") == "+201198765432"

    def test_rejects_none(self) -> None:
        assert normalize_egyptian_phone(None) is None

    def test_rejects_empty(self) -> None:
        assert normalize_egyptian_phone("") is None
        assert normalize_egyptian_phone("   ") is None

    def test_rejects_short_input(self) -> None:
        assert normalize_egyptian_phone("0119") is None
        assert normalize_egyptian_phone("+20119") is None

    def test_rejects_non_egyptian_country_code(self) -> None:
        # +44 (UK) must not slip through — we only accept EG mobiles.
        assert normalize_egyptian_phone("+441198765432") is None

    def test_rejects_letters(self) -> None:
        assert normalize_egyptian_phone("01198ABC5432") is None

    def test_rejects_ambiguous_no_prefix(self) -> None:
        # Ten raw digits without 0/20/+20 prefix — no way to know it's Egyptian.
        assert normalize_egyptian_phone("1198765432") is None


# ---------------------------------------------------------------------------
# ChurnRepository.get_by_customer_key
# ---------------------------------------------------------------------------


class TestChurnGetByCustomerKey:
    def _mk_session(self, row: dict | None) -> MagicMock:
        session = MagicMock()
        mapping_mock = MagicMock()
        mapping_mock.first.return_value = row
        chain = MagicMock()
        chain.mappings.return_value = mapping_mock
        session.execute.return_value = chain
        return session

    def test_returns_row_dict(self) -> None:
        session = self._mk_session(
            {
                "customer_key": 1234,
                "customer_name": "أستاذة منى",
                "health_score": 42.0,
                "health_band": "At Risk",
                "recency_days": 45,
                "frequency_3m": 1,
                "monetary_3m": 120,
                "trend": "declining",
                "rfm_segment": "At Risk",
                "churn_probability": 0.75,
                "risk_level": "high",
            },
        )
        repo = ChurnRepository(session)

        row = repo.get_by_customer_key(1234)

        assert row is not None
        assert row["customer_key"] == 1234
        assert row["risk_level"] == "high"
        # Parameters bound — no SQL injection surface.
        assert session.execute.call_args[0][1] == {"customer_key": 1234}

    def test_returns_none_when_not_found(self) -> None:
        session = self._mk_session(None)
        repo = ChurnRepository(session)
        assert repo.get_by_customer_key(9999) is None


# ---------------------------------------------------------------------------
# CustomerLookupService — orchestrates phone normaliser + contact + churn
# ---------------------------------------------------------------------------


def _mk_contact_session(contact_row: dict | None) -> MagicMock:
    """Mock the `SELECT ... FROM pos.customer_contact JOIN dim_customer` call."""
    session = MagicMock()
    mapping_mock = MagicMock()
    mapping_mock.first.return_value = contact_row
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    session.execute.return_value = chain
    return session


class TestCustomerLookupService:
    def test_returns_none_for_invalid_phone_shape(self) -> None:
        # Service short-circuits before hitting the DB on bad input.
        session = MagicMock()
        svc = CustomerLookupService(session)

        assert svc.lookup_by_phone("nonsense") is None
        # DB was never touched.
        session.execute.assert_not_called()

    def test_returns_none_when_phone_unknown(self) -> None:
        session = _mk_contact_session(None)
        svc = CustomerLookupService(session)

        assert svc.lookup_by_phone("01198765432") is None

    def test_returns_lookup_with_churn_risk(self) -> None:
        session = _mk_contact_session(
            {
                "customer_key": 1234,
                "phone_e164": "+201198765432",
                "customer_name": "أستاذة منى",
            },
        )

        with patch.object(
            ChurnRepository,
            "get_by_customer_key",
            return_value={"churn_probability": 0.8, "risk_level": "high"},
        ):
            svc = CustomerLookupService(session)
            result = svc.lookup_by_phone("01198765432")

        assert isinstance(result, PosCustomerLookup)
        assert result.customer_key == 1234
        assert result.phone == "+201198765432"
        assert result.churn.risk is True
        # Stubbed fields return neutral defaults until loyalty/credit tables land.
        assert result.loyalty_points == 0
        assert result.loyalty_tier is None
        assert result.outstanding_credit_egp == Decimal("0")

    def test_returns_lookup_without_churn_when_no_prediction(self) -> None:
        session = _mk_contact_session(
            {
                "customer_key": 7,
                "phone_e164": "+201198765432",
                "customer_name": "Ahmed",
            },
        )

        with patch.object(ChurnRepository, "get_by_customer_key", return_value=None):
            svc = CustomerLookupService(session)
            result = svc.lookup_by_phone("+201198765432")

        assert result is not None
        assert result.churn.risk is False
        assert result.churn.late_refills == []

    def test_low_probability_does_not_trigger_risk(self) -> None:
        session = _mk_contact_session(
            {
                "customer_key": 7,
                "phone_e164": "+201198765432",
                "customer_name": "Ahmed",
            },
        )

        with patch.object(
            ChurnRepository,
            "get_by_customer_key",
            return_value={"churn_probability": 0.2, "risk_level": "low"},
        ):
            svc = CustomerLookupService(session)
            result = svc.lookup_by_phone("+201198765432")

        assert result is not None
        assert result.churn.risk is False

    def test_service_passes_canonical_phone_to_db(self) -> None:
        session = _mk_contact_session(None)
        svc = CustomerLookupService(session)
        svc.lookup_by_phone("01198765432")

        call_kwargs = session.execute.call_args[0][1]
        assert call_kwargs == {"phone": "+201198765432"}
