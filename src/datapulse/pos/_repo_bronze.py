"""Bronze medallion write for POS transactions (bronze.pos_transactions).

Extracted from the original 1,187-LOC ``repository.py`` facade (see #543).
Methods preserve their SQL text and parameter order byte-for-byte.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from datapulse.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = get_logger(__name__)


class BronzeRepoMixin:
    """Mixin for :class:`PosRepository` — requires ``self._session`` set by __init__."""

    _session: Session

    def insert_bronze_pos_transaction(
        self,
        *,
        tenant_id: int,
        transaction_id: str,
        transaction_date: datetime,
        site_code: str,
        register_id: str | None,
        cashier_id: str,
        customer_id: str | None,
        drug_code: str,
        batch_number: str | None,
        quantity: Decimal,
        unit_price: Decimal,
        net_amount: Decimal,
        payment_method: str,
        discount: Decimal = Decimal("0"),
        insurance_no: str | None = None,
        is_return: bool = False,
        pharmacist_id: str | None = None,
    ) -> dict[str, Any]:
        """Write one line to bronze.pos_transactions for pipeline ingestion.

        The ``transaction_id`` must be prefixed with ``'POS-'`` by the caller
        (service layer) to prevent collision with ERP rows in fct_sales.
        (C3 fix from adversarial review.)
        """
        row = (
            self._session.execute(
                text("""
                    INSERT INTO bronze.pos_transactions
                        (tenant_id, source_type, transaction_id, transaction_date,
                         site_code, register_id, cashier_id, customer_id,
                         drug_code, batch_number, quantity, unit_price,
                         discount, net_amount, payment_method,
                         insurance_no, is_return, pharmacist_id)
                    VALUES
                        (:tenant_id, 'pos_api', :transaction_id, :transaction_date,
                         :site_code, :register_id, :cashier_id, :customer_id,
                         :drug_code, :batch_number, :quantity, :unit_price,
                         :discount, :net_amount, :payment_method,
                         :insurance_no, :is_return, :pharmacist_id)
                    ON CONFLICT (tenant_id, transaction_id, drug_code) DO NOTHING
                    RETURNING id, transaction_id, drug_code, net_amount, loaded_at
                """),
                {
                    "tenant_id": tenant_id,
                    "transaction_id": transaction_id,
                    "transaction_date": transaction_date,
                    "site_code": site_code,
                    "register_id": register_id,
                    "cashier_id": cashier_id,
                    "customer_id": customer_id,
                    "drug_code": drug_code,
                    "batch_number": batch_number,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                    "net_amount": net_amount,
                    "payment_method": payment_method,
                    "insurance_no": insurance_no,
                    "is_return": is_return,
                    "pharmacist_id": pharmacist_id,
                },
            )
            .mappings()
            .first()
        )
        # ON CONFLICT DO NOTHING returns no row on duplicate — that's intentional
        return dict(row) if row else {}
