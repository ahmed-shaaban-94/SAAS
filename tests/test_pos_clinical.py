"""Tests for the POS clinical panel — drug detail, cross-sell, alternatives (#623)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos._service_catalog import CatalogMixin
from datapulse.pos.models.clinical import AlternativeItem, CrossSellItem, DrugDetail
from datapulse.pos.repository import PosRepository

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PosRepository:
    return PosRepository(mock_session)


def _configure_execute(
    mock_session: MagicMock,
    rows: list[dict] | dict | None,
    *,
    mode: str,
) -> None:
    mapping_mock = MagicMock()
    if mode == "first":
        mapping_mock.first.return_value = rows
    elif mode == "all":
        mapping_mock.all.return_value = rows
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    mock_session.execute.return_value = chain


class _ServiceHarness(CatalogMixin):
    """Minimal harness exposing CatalogMixin methods with a mocked repo."""

    def __init__(self, repo: PosRepository) -> None:
        self._repo = repo
        self._inventory = MagicMock()


# ---------------------------------------------------------------------------
# Repository — SQL joins against pos.product_catalog_meta
# ---------------------------------------------------------------------------


class TestGetDrugDetail:
    def test_returns_detail_with_clinical_meta(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(
            mock_session,
            {
                "drug_code": "ANTIBIO-500",
                "drug_name": "Antibio 500mg",
                "drug_brand": "Acme",
                "drug_cluster": "Antibiotics",
                "drug_category": "rx",
                "unit_price": Decimal("45.0000"),
                "counseling_text": "Take with food. Complete the full course.",
                "active_ingredient": "amoxicillin",
            },
            mode="first",
        )

        row = repo.get_drug_detail("ANTIBIO-500")

        assert row is not None
        assert row["counseling_text"].startswith("Take with food")
        assert row["active_ingredient"] == "amoxicillin"
        # Parameter binding includes the drug_code literal, never interpolated.
        call_kwargs = mock_session.execute.call_args[0][1]
        assert call_kwargs == {"drug_code": "ANTIBIO-500"}

    def test_returns_none_for_unknown_drug(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(mock_session, None, mode="first")
        assert repo.get_drug_detail("UNKNOWN") is None

    def test_sql_uses_left_join_so_meta_is_optional(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(mock_session, None, mode="first")
        repo.get_drug_detail("X")
        sql = str(mock_session.execute.call_args[0][0])
        # Without LEFT JOIN, drugs without clinical metadata would never resolve.
        assert "LEFT" in sql and "JOIN pos.product_catalog_meta" in sql


class TestGetCrossSellRules:
    def test_returns_joined_rows(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(
            mock_session,
            [
                {
                    "drug_code": "PROBIO-1",
                    "drug_name": "Probio Plus",
                    "reason": "Restore gut flora during antibiotic therapy",
                    "reason_tag": "PROTECT",
                    "unit_price": Decimal("70.0000"),
                },
            ],
            mode="all",
        )

        rows = repo.get_cross_sell_rules("ANTIBIO-500")
        assert len(rows) == 1
        assert rows[0]["reason_tag"] == "PROTECT"

    def test_empty_when_no_rules(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(mock_session, [], mode="all")
        assert repo.get_cross_sell_rules("UNKNOWN") == []


class TestGetAlternativesByIngredient:
    def test_returns_siblings_with_primary_price(
        self,
        repo: PosRepository,
        mock_session: MagicMock,
    ) -> None:
        _configure_execute(
            mock_session,
            [
                {
                    "drug_code": "GENERIC-500",
                    "drug_name": "Generic 500mg",
                    "unit_price": Decimal("30.0000"),
                    "primary_unit_price": Decimal("45.0000"),
                },
                {
                    "drug_code": "PRICIER-500",
                    "drug_name": "Pricier 500mg",
                    "unit_price": Decimal("60.0000"),
                    "primary_unit_price": Decimal("45.0000"),
                },
            ],
            mode="all",
        )

        rows = repo.get_alternatives_by_ingredient("ANTIBIO-500")
        assert len(rows) == 2
        # Repo doesn't filter; service layer drops the pricier sibling.


# ---------------------------------------------------------------------------
# Service — converts repo rows to Pydantic + filters pricier alternatives
# ---------------------------------------------------------------------------


class TestServiceGetDrugDetail:
    def test_returns_drug_detail_with_meta(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_drug_detail.return_value = {
            "drug_code": "ANTIBIO-500",
            "drug_name": "Antibio 500mg",
            "drug_brand": "Acme",
            "drug_cluster": "Antibiotics",
            "drug_category": "rx",
            "unit_price": Decimal("45.00"),
            "counseling_text": "Take with food.",
            "active_ingredient": "amoxicillin",
        }
        svc = _ServiceHarness(mock_repo)

        detail = svc.get_drug_detail("ANTIBIO-500")

        assert isinstance(detail, DrugDetail)
        assert detail.counseling_text == "Take with food."
        assert detail.active_ingredient == "amoxicillin"
        assert detail.unit_price == Decimal("45.00")

    def test_returns_detail_without_meta_fields_null(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_drug_detail.return_value = {
            "drug_code": "BARE-100",
            "drug_name": "Bare 100mg",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": None,
            "unit_price": 0,
            "counseling_text": None,
            "active_ingredient": None,
        }
        svc = _ServiceHarness(mock_repo)

        detail = svc.get_drug_detail("BARE-100")
        assert detail is not None
        assert detail.counseling_text is None
        assert detail.active_ingredient is None

    def test_returns_none_for_unknown_drug(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_drug_detail.return_value = None
        svc = _ServiceHarness(mock_repo)
        assert svc.get_drug_detail("UNKNOWN") is None


class TestServiceGetCrossSell:
    def test_returns_frozen_models(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_cross_sell_rules.return_value = [
            {
                "drug_code": "PROBIO-1",
                "drug_name": "Probio Plus",
                "reason": "Restore gut flora",
                "reason_tag": "PROTECT",
                "unit_price": Decimal("70.00"),
            }
        ]
        svc = _ServiceHarness(mock_repo)

        items = svc.get_cross_sell("ANTIBIO-500")
        assert len(items) == 1
        assert isinstance(items[0], CrossSellItem)
        assert items[0].reason_tag == "PROTECT"

    def test_empty_list_when_no_rules(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_cross_sell_rules.return_value = []
        svc = _ServiceHarness(mock_repo)
        assert svc.get_cross_sell("X") == []


class TestServiceGetAlternatives:
    def test_filters_out_pricier_siblings(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_alternatives_by_ingredient.return_value = [
            {
                "drug_code": "CHEAPER",
                "drug_name": "Cheaper 500mg",
                "unit_price": Decimal("30.00"),
                "primary_unit_price": Decimal("45.00"),
            },
            {
                "drug_code": "PRICIER",
                "drug_name": "Pricier 500mg",
                "unit_price": Decimal("60.00"),
                "primary_unit_price": Decimal("45.00"),
            },
            {
                "drug_code": "EQUAL",
                "drug_name": "Equal 500mg",
                "unit_price": Decimal("45.00"),
                "primary_unit_price": Decimal("45.00"),
            },
        ]
        svc = _ServiceHarness(mock_repo)

        alts = svc.get_alternatives("ANTIBIO-500")
        # Only the cheaper sibling survives (pricier + equal are filtered).
        assert len(alts) == 1
        assert isinstance(alts[0], AlternativeItem)
        assert alts[0].drug_code == "CHEAPER"
        assert alts[0].savings_egp == Decimal("15.00")

    def test_empty_when_no_ingredient_on_file(self) -> None:
        mock_repo = MagicMock()
        # Repo returns [] when the primary has no active_ingredient.
        mock_repo.get_alternatives_by_ingredient.return_value = []
        svc = _ServiceHarness(mock_repo)
        assert svc.get_alternatives("NO-INGREDIENT") == []
