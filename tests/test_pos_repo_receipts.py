"""Unit tests for PosRepository — receipt save and retrieval."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest

from datapulse.pos.repository import PosRepository

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PosRepository:
    return PosRepository(mock_session)


def _make_execute(rows, *, mode: str = "one"):
    mapping_mock = MagicMock()
    if mode == "one":
        mapping_mock.one.return_value = rows
    elif mode == "first":
        mapping_mock.first.return_value = rows
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    return chain


class TestSaveReceipt:
    def test_saves_thermal_receipt(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 1,
            "transaction_id": 100,
            "tenant_id": 1,
            "format": "thermal",
            "file_path": None,
            "generated_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.save_receipt(transaction_id=100, tenant_id=1, fmt="thermal", content=b"\x1b@")
        assert result["format"] == "thermal"
        params = mock_session.execute.call_args[0][1]
        assert params["fmt"] == "thermal"
        assert params["content"] == b"\x1b@"

    def test_saves_pdf_receipt_with_path(self, repo: PosRepository, mock_session: MagicMock):
        expected = {
            "id": 2,
            "transaction_id": 100,
            "tenant_id": 1,
            "format": "pdf",
            "file_path": "/receipts/receipt-100.pdf",
            "generated_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(expected, mode="one")
        result = repo.save_receipt(
            transaction_id=100,
            tenant_id=1,
            fmt="pdf",
            file_path="/receipts/receipt-100.pdf",
        )
        assert result["file_path"] == "/receipts/receipt-100.pdf"


class TestGetReceipt:
    def test_returns_most_recent_receipt(self, repo: PosRepository, mock_session: MagicMock):
        row = {
            "id": 1,
            "transaction_id": 100,
            "tenant_id": 1,
            "format": "pdf",
            "content": b"%PDF",
            "file_path": None,
            "generated_at": datetime.datetime(2026, 4, 15),
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_receipt(100, "pdf", tenant_id=1)
        assert result["content"] == b"%PDF"

    def test_returns_none_when_not_found(self, repo: PosRepository, mock_session: MagicMock):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        assert repo.get_receipt(999, "thermal", tenant_id=1) is None
