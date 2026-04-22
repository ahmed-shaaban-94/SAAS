"""One-shot AST-based extractor: split src/datapulse/pos/repository.py into
per-domain mixin modules. Every method body is preserved byte-for-byte.

After running this script:
  * New files: src/datapulse/pos/_repo_{terminal,transaction,shift,voidreturn,
               catalog,bronze}.py
  * repository.py becomes a thin facade that inherits from the mixins.

Run from repo root:  python scripts/split_pos_repository.py
"""

from __future__ import annotations

import ast
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "datapulse" / "pos" / "repository.py"

# Methods to extract, grouped by target mixin file.
GROUPS: dict[str, tuple[str, list[str]]] = {
    "_repo_terminal.py": (
        "TerminalRepoMixin",
        [
            "create_terminal_session",
            "update_terminal_status",
            "get_terminal_session",
            "get_active_terminals",
        ],
    ),
    "_repo_transaction.py": (
        "TransactionRepoMixin",
        [
            "create_transaction",
            "get_transaction",
            "update_transaction_status",
            "list_transactions",
            "add_transaction_item",
            "update_item_quantity",
            "remove_item",
            "get_transaction_items",
            "save_receipt",
            "get_receipt",
        ],
    ),
    "_repo_shift.py": (
        "ShiftRepoMixin",
        [
            "create_shift_record",
            "update_shift_record",
            "get_current_shift",
            "list_shifts",
            "get_shift_by_id",
            "get_shift_summary_data",
            "record_cash_event",
            "get_cash_events",
        ],
    ),
    "_repo_voidreturn.py": (
        "VoidReturnRepoMixin",
        [
            "create_void_log",
            "get_void_log",
            "list_returns",
            "create_return",
            "get_return",
            "list_returns_for_transaction",
            "get_returned_quantities_for_transaction",
        ],
    ),
    "_repo_catalog.py": (
        "CatalogRepoMixin",
        [
            "search_dim_products",
            "get_product_by_code",
            "list_catalog_products",
            "list_catalog_stock",
            "get_pharmacist_pin_hash",
        ],
    ),
    "_repo_bronze.py": (
        "BronzeRepoMixin",
        [
            "insert_bronze_pos_transaction",
        ],
    ),
}

HEADER_TEMPLATE = '''"""{docstring}

Extracted from the original 1,187-LOC ``repository.py`` facade (see #543).
Methods preserve their SQL text and parameter order byte-for-byte.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from datapulse.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = get_logger(__name__)


class {classname}:
    """Mixin for :class:`PosRepository` — requires ``self._session`` set by __init__."""

    _session: Session

'''

DOCSTRINGS = {
    "TerminalRepoMixin": "Terminal-session table access (pos.terminal_sessions).",
    "TransactionRepoMixin": (
        "Transactions + items + receipts table access.\n\n"
        "Covers pos.transactions, pos.transaction_items, pos.receipts."
    ),
    "ShiftRepoMixin": (
        "Shifts + cash drawer events table access.\n\n"
        "Covers pos.shift_records and pos.cash_drawer_events."
    ),
    "VoidReturnRepoMixin": (
        "Void log + returns table access (pos.void_log / pos.returns + joins)."
    ),
    "CatalogRepoMixin": (
        "Read-only product catalog + pharmacist PIN lookup.\n\n"
        "Sources: public_marts.dim_product, public_staging.stg_batches,\n"
        "public.tenant_members (for PIN hash)."
    ),
    "BronzeRepoMixin": ("Bronze medallion write for POS transactions (bronze.pos_transactions)."),
}


def main() -> None:
    source = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    tree = ast.parse("".join(source))

    # Locate PosRepository class and its methods
    (cls,) = (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "PosRepository")
    methods_by_name = {
        n.name: n for n in cls.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    }

    # Extract per-method source (line numbers are 1-indexed, inclusive on both ends)
    def method_source(m: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        start = m.lineno - 1
        # end_lineno covers docstring + body, but we also want trailing blank lines
        # inside the class — ast already handles that.
        end = m.end_lineno or m.lineno
        return "".join(source[start:end]) + "\n"

    out_dir = SRC.parent
    for filename, (classname, method_names) in GROUPS.items():
        header = HEADER_TEMPLATE.format(docstring=DOCSTRINGS[classname], classname=classname)
        bodies = []
        for name in method_names:
            m = methods_by_name[name]
            src = method_source(m)
            # Methods are already indented 4 spaces (they were inside a class).
            bodies.append(src)
        content = header + "\n".join(bodies).rstrip() + "\n"
        (out_dir / filename).write_text(content, encoding="utf-8")
        print(f"wrote {filename} ({classname}, {len(method_names)} methods)")

    # Write the slim facade
    facade = '''"""POS repository — facade that composes per-domain mixins.

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
):
    """Raw SQL access for all POS tables in the ``pos`` and ``bronze`` schemas.

    Constructor takes a SQLAlchemy ``Session`` scoped to the current request.
    All queries are parameterised — no string interpolation.

    The class is intentionally a thin composition of domain mixins; the
    shared ``self._session`` is the only state every mixin needs.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
'''
    SRC.write_text(facade, encoding="utf-8")
    print("wrote repository.py (facade, 6 mixins)")


if __name__ == "__main__":
    main()
