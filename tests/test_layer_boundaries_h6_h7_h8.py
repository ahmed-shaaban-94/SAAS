"""Layer-boundary violation tests — H6 / H7 / H8.

Each group starts with the failing RED assertion; GREEN follows in the
corresponding source files.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# H6 — _service_catalog.py must not import fastapi
# ---------------------------------------------------------------------------


class TestH6NofastapiInServiceCatalog:
    def test_service_catalog_module_does_not_import_fastapi(self) -> None:
        """The service layer must never import fastapi — that's the route layer's job.

        Uses an AST walk so string literals and comments containing "fastapi"
        don't produce false positives.
        """
        src = pathlib.Path("src/datapulse/pos/_service_catalog.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not (alias.name or "").startswith("fastapi"), (
                        f"fastapi import found at line {node.lineno}"
                    )
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("fastapi"), (
                    f"from fastapi import found at line {node.lineno}"
                )

    def test_regenerate_receipt_raises_pos_not_found_error(self) -> None:
        """_regenerate_receipt must raise PosNotFoundError, not HTTPException."""
        from datapulse.pos._service_catalog import CatalogMixin
        from datapulse.pos.exceptions import PosNotFoundError

        mixin = object.__new__(CatalogMixin)

        mock_repo = MagicMock()
        mock_repo.get_transaction.return_value = None  # trigger the not-found branch

        mixin._repo = mock_repo  # type: ignore[attr-defined]

        with pytest.raises(PosNotFoundError) as exc_info:
            mixin._regenerate_receipt(999, tenant_id=1, fmt="pdf")

        assert exc_info.value.http_status == 404


class TestH6RouteStillReturns404:
    """The route must still surface 404 after the service raises PosNotFoundError."""

    def test_receipt_route_returns_404_when_transaction_missing(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from datapulse.api.auth import get_current_user
        from datapulse.api.bootstrap.exceptions import install_exception_handlers
        from datapulse.api.deps import get_pos_service
        from datapulse.api.routes._pos_receipts import router
        from datapulse.pos.exceptions import PosNotFoundError

        app = FastAPI()
        install_exception_handlers(app)
        app.include_router(router, prefix="/pos")

        mock_service = MagicMock()
        mock_service.get_receipt_pdf.side_effect = PosNotFoundError("transaction_not_found")

        mock_user = {"sub": "test", "tenant_id": "1"}

        app.dependency_overrides[get_pos_service] = lambda: mock_service
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/pos/receipts/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "transaction_not_found"


# ---------------------------------------------------------------------------
# H7a — CustomerContactRepository must own the contact-lookup SQL
# ---------------------------------------------------------------------------


class TestH7aCustomerContactRepository:
    def test_customer_contact_repository_exists(self) -> None:
        """CustomerContactRepository must exist in its own module."""
        from datapulse.pos import customer_contact_repository  # noqa: F401

    def test_repository_returns_row_dict(self) -> None:
        from datapulse.pos.customer_contact_repository import CustomerContactRepository

        session = MagicMock()
        mapping_mock = MagicMock()
        mapping_mock.first.return_value = {
            "customer_key": 42,
            "phone_e164": "+201198765432",
            "customer_name": "Ahmed",
        }
        chain = MagicMock()
        chain.mappings.return_value = mapping_mock
        session.execute.return_value = chain

        repo = CustomerContactRepository(session)
        row = repo.find_by_phone("+201198765432")

        assert row is not None
        assert row["customer_key"] == 42
        # Must have bound :phone param — not SQL injection surface.
        call_params = session.execute.call_args[0][1]
        assert call_params == {"phone": "+201198765432"}

    def test_repository_returns_none_when_not_found(self) -> None:
        from datapulse.pos.customer_contact_repository import CustomerContactRepository

        session = MagicMock()
        mapping_mock = MagicMock()
        mapping_mock.first.return_value = None
        chain = MagicMock()
        chain.mappings.return_value = mapping_mock
        session.execute.return_value = chain

        repo = CustomerContactRepository(session)
        assert repo.find_by_phone("+201999999999") is None

    def test_service_no_longer_imports_sqlalchemy_text(self) -> None:
        """After the refactor the service must not hold a direct sqlalchemy.text import."""
        src = pathlib.Path("src/datapulse/pos/customer_lookup_service.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("sqlalchemy"):
                names = [alias.name for alias in node.names]
                assert "text" not in names, (
                    f"customer_lookup_service.py imports 'text' from sqlalchemy at line "
                    f"{node.lineno} — SQL belongs in the repository layer"
                )


# ---------------------------------------------------------------------------
# H7b — ChurnRepositoryProtocol boundary
# ---------------------------------------------------------------------------


class TestH7bChurnRepositoryProtocol:
    def test_protocol_exists_and_has_get_by_customer_key(self) -> None:
        from datapulse.pos.customer_lookup_service import ChurnRepositoryProtocol

        assert hasattr(ChurnRepositoryProtocol, "get_by_customer_key")

    def test_service_accepts_protocol_typed_churn_repo(self) -> None:
        """Service constructor must accept (contact_repo, churn_repo) not just session."""
        from datapulse.pos.customer_lookup_service import CustomerLookupService

        sig = inspect.signature(CustomerLookupService.__init__)
        params = list(sig.parameters.keys())
        assert "contact_repo" in params, f"Expected 'contact_repo' param, got {params}"
        assert "churn_repo" in params, f"Expected 'churn_repo' param, got {params}"
        assert "session" not in params, "session should be gone from CustomerLookupService.__init__"

    def test_concrete_churn_repository_satisfies_protocol(self) -> None:
        from datapulse.analytics.churn_repository import ChurnRepository

        # Structural check: ChurnRepository must implement the Protocol's method.
        assert hasattr(ChurnRepository, "get_by_customer_key")

    def test_lookup_uses_injected_contact_repo(self) -> None:
        """Service must call contact_repo.find_by_phone, not session.execute."""
        from datapulse.pos.customer_lookup_service import CustomerLookupService

        mock_contact = MagicMock()
        mock_contact.find_by_phone.return_value = None

        mock_churn = MagicMock()

        svc = CustomerLookupService(mock_contact, mock_churn)
        result = svc.lookup_by_phone("01198765432")

        assert result is None
        mock_contact.find_by_phone.assert_called_once_with("+201198765432")

    def test_lookup_uses_injected_churn_repo(self) -> None:
        from datapulse.pos.customer_lookup_service import CustomerLookupService

        mock_contact = MagicMock()
        mock_contact.find_by_phone.return_value = {
            "customer_key": 7,
            "phone_e164": "+201198765432",
            "customer_name": "Test",
        }

        mock_churn = MagicMock()
        mock_churn.get_by_customer_key.return_value = {
            "churn_probability": 0.9,
            "risk_level": "high",
        }

        svc = CustomerLookupService(mock_contact, mock_churn)
        result = svc.lookup_by_phone("+201198765432")

        assert result is not None
        assert result.churn.risk is True
        mock_churn.get_by_customer_key.assert_called_once_with(7)


# ---------------------------------------------------------------------------
# H8 — Decimal preservation through reorder_service → repo
# ---------------------------------------------------------------------------


class TestH8DecimalPreservation:
    def test_upsert_config_repo_signature_accepts_decimal(self) -> None:
        """upsert_config must declare Decimal params, not float.

        Uses get_type_hints() to resolve string annotations from
        ``from __future__ import annotations``.
        """
        import typing

        from datapulse.inventory.reorder_repository import ReorderConfigRepository

        hints = typing.get_type_hints(ReorderConfigRepository.upsert_config)
        for field in ("min_stock", "reorder_point", "max_stock"):
            assert hints[field] is Decimal, (
                f"ReorderConfigRepository.upsert_config param '{field}' "
                f"should be Decimal, got {hints[field]}"
            )

    def test_service_does_not_cast_decimal_to_float(self) -> None:
        """The float() casts on Decimal fields must be removed from the service."""
        import ast
        import pathlib

        src = pathlib.Path("src/datapulse/inventory/reorder_service.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "float"
                and node.args
                and isinstance(node.args[0], ast.Attribute)
                and node.args[0].attr in ("min_stock", "reorder_point", "max_stock")
            ):
                attr = node.args[0].attr
                pytest.fail(
                    f"float({attr}) cast found in reorder_service.py at "
                    f"line {node.lineno} — Decimal fields must not be cast"
                )

    def test_decimal_value_reaches_repo_unchanged(self) -> None:
        """Decimal('99.999') must arrive at repo.upsert_config as Decimal, not float."""
        from datapulse.inventory.reorder_repository import ReorderConfig
        from datapulse.inventory.reorder_service import ReorderConfigRequest, ReorderConfigService

        mock_repo = MagicMock()
        mock_repo.upsert_config.return_value = ReorderConfig(
            id=1,
            tenant_id=1,
            drug_code="D001",
            site_code="S01",
            min_stock=Decimal("99.999"),
            reorder_point=Decimal("99.999"),
            max_stock=Decimal("99.999"),
            reorder_lead_days=1,
            is_active=True,
        )

        svc = ReorderConfigService(mock_repo)
        req = ReorderConfigRequest(
            drug_code="D001",
            site_code="S01",
            min_stock=Decimal("99.999"),
            reorder_point=Decimal("99.999"),
            max_stock=Decimal("99.999"),
            reorder_lead_days=1,
        )
        svc.upsert_config(tenant_id=1, request=req)

        call_kwargs = mock_repo.upsert_config.call_args[1]
        assert isinstance(call_kwargs["min_stock"], Decimal), (
            f"min_stock was {type(call_kwargs['min_stock'])}, expected Decimal"
        )
        assert call_kwargs["min_stock"] == Decimal("99.999"), (
            "Decimal value was truncated or coerced"
        )
