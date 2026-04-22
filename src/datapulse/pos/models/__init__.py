"""Pydantic request/response models for the POS module.

All models are frozen (immutable) to prevent accidental mutation after
construction. Financial fields use ``JsonDecimal`` (``Decimal`` internally,
``float`` in JSON) for precision without JS string-parsing issues.

This module is a package — the 60+ models are grouped by concern into
11 sub-modules and re-exported here so existing
``from datapulse.pos.models import X`` imports keep working.

Split under issue #543 (the previous 1,081-LOC single-file ``models.py``).
Grouping:

- ``cart``        — ``PosCartItem`` (shared line-item primitive)
- ``terminal``    — terminal sessions + active-terminal status
- ``transaction`` — transaction header + list/detail + item requests
- ``checkout``    — checkout + void + atomic-commit + ``AppliedDiscount``
- ``returns``     — return request/response + detail
- ``shift``       — shift lifecycle + cash drawer + close-v2
- ``products``    — product search, stock, batches, catalog pull, email
- ``pharmacist``  — controlled-substance PIN verification
- ``offline``     — capabilities, tenant keys, device reg, grants, override tokens
- ``vouchers``    — Phase 1 voucher engine
- ``promotions``  — Phase 2 promotion engine
"""

from datapulse.pos.models.cart import PosCartItem
from datapulse.pos.models.checkout import (
    AppliedDiscount,
    CheckoutRequest,
    CheckoutResponse,
    CommitRequest,
    CommitResponse,
    VoidRequest,
    VoidResponse,
)
from datapulse.pos.models.clinical import (
    AlternativeItem,
    CrossSellItem,
    DrugDetail,
)
from datapulse.pos.models.commission import ActiveShiftResponse
from datapulse.pos.models.customer import (
    LateRefillItem,
    PosCustomerChurn,
    PosCustomerLookup,
)
from datapulse.pos.models.offline import (
    CapabilitiesDoc,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    OfflineGrantEnvelope,
    OfflineGrantPayload,
    OverrideCodeEntry,
    OverrideTokenClaim,
    OverrideTokenEnvelope,
    RoleSnapshot,
    TenantKeysResponse,
    TenantPublicKey,
)
from datapulse.pos.models.pharmacist import (
    PharmacistVerifyRequest,
    PharmacistVerifyResponse,
)
from datapulse.pos.models.products import (
    BatchSummary,
    CatalogProductEntry,
    CatalogProductPage,
    CatalogStockEntry,
    CatalogStockPage,
    EmailReceiptRequest,
    PosProductResult,
    PosStockInfo,
)
from datapulse.pos.models.promotions import (
    EligibleCartItem,
    EligiblePromotion,
    EligiblePromotionsRequest,
    EligiblePromotionsResponse,
    PromotionApplicationRow,
    PromotionCreate,
    PromotionDiscountType,
    PromotionNameStr,
    PromotionResponse,
    PromotionScope,
    PromotionStatus,
    PromotionStatusUpdate,
    PromotionUpdate,
)
from datapulse.pos.models.returns import (
    ReturnDetailResponse,
    ReturnRequest,
    ReturnResponse,
)
from datapulse.pos.models.shift import (
    CashCountRequest,
    CashDrawerEventResponse,
    CloseShiftRequest,
    CloseShiftRequestV2,
    LocalUnresolvedClaim,
    ShiftRecord,
    ShiftSummaryResponse,
    StartShiftRequest,
)
from datapulse.pos.models.terminal import (
    ActiveForMeResponse,
    ActiveTerminalRow,
    TerminalCloseRequest,
    TerminalOpenRequest,
    TerminalSession,
    TerminalSessionResponse,
)
from datapulse.pos.models.transaction import (
    AddItemRequest,
    PosTransaction,
    TransactionDetailResponse,
    TransactionResponse,
    UpdateItemRequest,
)
from datapulse.pos.models.vouchers import (
    VoucherCodeStr,
    VoucherCreate,
    VoucherResponse,
    VoucherStatus,
    VoucherType,
    VoucherValidateRequest,
    VoucherValidateResponse,
)

__all__ = [
    # cart
    "PosCartItem",
    # clinical
    "AlternativeItem",
    "CrossSellItem",
    "DrugDetail",
    # commission / active shift
    "ActiveShiftResponse",
    # customer lookup
    "LateRefillItem",
    "PosCustomerChurn",
    "PosCustomerLookup",
    # checkout
    "AppliedDiscount",
    "CheckoutRequest",
    "CheckoutResponse",
    "CommitRequest",
    "CommitResponse",
    "VoidRequest",
    "VoidResponse",
    # offline
    "CapabilitiesDoc",
    "DeviceRegisterRequest",
    "DeviceRegisterResponse",
    "OfflineGrantEnvelope",
    "OfflineGrantPayload",
    "OverrideCodeEntry",
    "OverrideTokenClaim",
    "OverrideTokenEnvelope",
    "RoleSnapshot",
    "TenantKeysResponse",
    "TenantPublicKey",
    # pharmacist
    "PharmacistVerifyRequest",
    "PharmacistVerifyResponse",
    # products
    "BatchSummary",
    "CatalogProductEntry",
    "CatalogProductPage",
    "CatalogStockEntry",
    "CatalogStockPage",
    "EmailReceiptRequest",
    "PosProductResult",
    "PosStockInfo",
    # promotions
    "EligibleCartItem",
    "EligiblePromotion",
    "EligiblePromotionsRequest",
    "EligiblePromotionsResponse",
    "PromotionApplicationRow",
    "PromotionCreate",
    "PromotionDiscountType",
    "PromotionNameStr",
    "PromotionResponse",
    "PromotionScope",
    "PromotionStatus",
    "PromotionStatusUpdate",
    "PromotionUpdate",
    # returns
    "ReturnDetailResponse",
    "ReturnRequest",
    "ReturnResponse",
    # shift
    "CashCountRequest",
    "CashDrawerEventResponse",
    "CloseShiftRequest",
    "CloseShiftRequestV2",
    "LocalUnresolvedClaim",
    "ShiftRecord",
    "ShiftSummaryResponse",
    "StartShiftRequest",
    # terminal
    "ActiveForMeResponse",
    "ActiveTerminalRow",
    "TerminalCloseRequest",
    "TerminalOpenRequest",
    "TerminalSession",
    "TerminalSessionResponse",
    # transaction
    "AddItemRequest",
    "PosTransaction",
    "TransactionDetailResponse",
    "TransactionResponse",
    "UpdateItemRequest",
    # vouchers
    "VoucherCodeStr",
    "VoucherCreate",
    "VoucherResponse",
    "VoucherStatus",
    "VoucherType",
    "VoucherValidateRequest",
    "VoucherValidateResponse",
]
