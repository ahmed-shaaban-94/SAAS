"""POS repository — facade that composes per-domain mixins.

Follows the Route->Service->Repository pattern. All methods accept / return
plain dicts (or None). The service layer is responsible for constructing
Pydantic models from these dicts. Financial columns are stored as NUMERIC(18,4);
Python receives them as Decimal.

The actual SQL lives in per-domain mixin modules (see ``_repo_*.py``); this
module owns only the session wiring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from datapulse.pos._repo_bronze import BronzeRepoMixin
from datapulse.pos._repo_catalog import CatalogRepoMixin
from datapulse.pos._repo_delivery import DeliveryRepoMixin
from datapulse.pos._repo_shift import ShiftRepoMixin
from datapulse.pos._repo_terminal import TerminalRepoMixin
from datapulse.pos._repo_transaction import TransactionRepoMixin
from datapulse.pos._repo_voidreturn import VoidReturnRepoMixin

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class PosRepository(
    TerminalRepoMixin,
    TransactionRepoMixin,
    ShiftRepoMixin,
    VoidReturnRepoMixin,
    CatalogRepoMixin,
    BronzeRepoMixin,
    DeliveryRepoMixin,
):
    """Raw SQL access for all POS tables in the ``pos`` and ``bronze`` schemas.

    Constructor takes a SQLAlchemy ``Session`` scoped to the current request.
    All queries are parameterised — no string interpolation.

    The class is intentionally a thin composition of domain mixins; the
    shared ``self._session`` is the only state every mixin needs.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
