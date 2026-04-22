"""Clinical panel models — drug detail, cross-sell, and alternatives.

Powers the column-3 clinical panel in the POS v9 terminal (#623). All models
are frozen to match the rest of the POS model surface.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datapulse.types import JsonDecimal


class DrugDetail(BaseModel):
    """Drug detail response — dim_product core fields plus POS-owned clinical meta.

    ``counseling_text`` is the cyan-bubble tip shown in the clinical panel;
    ``null`` when the drug has no guidance on file. Frontend contract is
    ``string | null`` so the card can hide cleanly (#623).
    """

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    drug_brand: str | None = None
    drug_cluster: str | None = None
    drug_category: str | None = None
    unit_price: JsonDecimal
    counseling_text: str | None = None
    active_ingredient: str | None = None


class CrossSellItem(BaseModel):
    """One cross-sell recommendation for a primary drug.

    ``reason_tag`` is an uppercase short tag (e.g. ``ROUTE``, ``PROTECT``);
    unknown tags fall back to a neutral pill style in the UI.
    """

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    reason: str
    reason_tag: str
    unit_price: JsonDecimal


class AlternativeItem(BaseModel):
    """One generic alternative for a primary drug, with savings vs the primary.

    ``savings_egp`` = primary.unit_price − alt.unit_price; zero or negative
    alternatives are filtered out server-side so the UI only surfaces true
    cost-savers.
    """

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_name: str
    unit_price: JsonDecimal
    savings_egp: JsonDecimal
