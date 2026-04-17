"""Curated pharma sample dataset for onboarding (Phase 2 Task 2 / #401).

Provides a deterministic 5 000-row synthetic dataset that looks like a small
Egyptian 10-branch pharma chain — no PII, no real patient data, no real
customer identifiers. Used by the "Use sample pharma data" CTA on the
upload wizard so a first-time user can reach a populated dashboard without
having to prepare a file.

Idempotency: every sample row is tagged with `source_file='sample.csv'`
and `source_quarter='SAMPLE'`. Reload = DELETE on those markers + INSERT.

RLS: every row carries `tenant_id`. The caller passes the current tenant;
the insertion helper refuses if the row-level `tenant_id` does not match.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)

SAMPLE_SOURCE_FILE = "sample.csv"
SAMPLE_SOURCE_QUARTER = "SAMPLE"
_DEFAULT_ROW_COUNT = 5000
_INSERT_BATCH_SIZE = 500
_DATE_WINDOW_DAYS = 180

# 10 branches — generic Egyptian city codes, no real pharmacy names.
_SITES: tuple[tuple[str, str], ...] = (
    ("S01", "Cairo Downtown"),
    ("S02", "Cairo Heliopolis"),
    ("S03", "Cairo Nasr City"),
    ("S04", "Giza Mohandessin"),
    ("S05", "Giza 6th October"),
    ("S06", "Alexandria Smouha"),
    ("S07", "Alexandria Roushdy"),
    ("S08", "Mansoura Central"),
    ("S09", "Tanta Main"),
    ("S10", "Port Said Harbor"),
)

# 8 categories × 6–7 products each, ~55 SKUs total. Names are generic
# therapeutic-class descriptors, not branded drugs.
_CATALOG: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Analgesics",
        "Generic Brand A",
        (
            "Paracetamol 500mg Tab",
            "Ibuprofen 400mg Tab",
            "Aspirin 81mg Tab",
            "Diclofenac 50mg Tab",
            "Naproxen 250mg Tab",
            "Tramadol 50mg Cap",
        ),
    ),
    (
        "Antibiotics",
        "Generic Brand B",
        (
            "Amoxicillin 500mg Cap",
            "Azithromycin 500mg Tab",
            "Ciprofloxacin 500mg Tab",
            "Doxycycline 100mg Cap",
            "Cefuroxime 250mg Tab",
            "Clarithromycin 500mg Tab",
        ),
    ),
    (
        "Antihypertensives",
        "Generic Brand C",
        (
            "Amlodipine 5mg Tab",
            "Lisinopril 10mg Tab",
            "Losartan 50mg Tab",
            "Metoprolol 25mg Tab",
            "Hydrochlorothiazide 25mg Tab",
            "Bisoprolol 5mg Tab",
        ),
    ),
    (
        "Antidiabetics",
        "Generic Brand D",
        (
            "Metformin 500mg Tab",
            "Gliclazide 30mg Tab",
            "Sitagliptin 100mg Tab",
            "Empagliflozin 10mg Tab",
            "Insulin Glargine 100U/mL",
            "Pioglitazone 15mg Tab",
        ),
    ),
    (
        "Gastro",
        "Generic Brand E",
        (
            "Omeprazole 20mg Cap",
            "Pantoprazole 40mg Tab",
            "Ranitidine 150mg Tab",
            "Domperidone 10mg Tab",
            "Loperamide 2mg Cap",
            "Simethicone 40mg Tab",
        ),
    ),
    (
        "Respiratory",
        "Generic Brand F",
        (
            "Salbutamol Inhaler 100mcg",
            "Budesonide Inhaler 200mcg",
            "Montelukast 10mg Tab",
            "Loratadine 10mg Tab",
            "Cetirizine 10mg Tab",
            "Fexofenadine 120mg Tab",
        ),
    ),
    (
        "Vitamins",
        "Generic Brand G",
        (
            "Vitamin D3 1000IU Tab",
            "Multivitamin Tab",
            "Vitamin C 500mg Tab",
            "Folic Acid 5mg Tab",
            "Ferrous Sulfate 200mg Tab",
            "Calcium 500mg Tab",
        ),
    ),
    (
        "Dermatology",
        "Generic Brand H",
        (
            "Hydrocortisone Cream 1%",
            "Clotrimazole Cream 1%",
            "Mupirocin Ointment",
            "Benzoyl Peroxide Gel 5%",
            "Tretinoin Cream 0.025%",
            "Moisturizing Cream",
        ),
    ),
)

_CUSTOMER_NAMES: tuple[tuple[str, str], ...] = (
    ("C001", "Walk-In Customer"),
    ("C002", "Sunrise Medical Group"),
    ("C003", "Nile Valley Clinic"),
    ("C004", "Al Azhar Health Network"),
    ("C005", "Mediterranean Wellness"),
    ("C006", "Delta Family Practice"),
    ("C007", "Red Sea Emergency Unit"),
    ("C008", "Giza Care Cooperative"),
    ("C009", "Alexandria Women's Center"),
    ("C010", "Port Clinic Urgent Care"),
)

_STAFF: tuple[tuple[str, str, str], ...] = (
    ("E101", "Ahmed Fahmy", "Pharmacist"),
    ("E102", "Mona El-Sayed", "Senior Pharmacist"),
    ("E103", "Karim Adel", "Pharmacist"),
    ("E104", "Nourhan Hassan", "Pharmacist"),
    ("E105", "Omar Kamel", "Pharmacy Tech"),
    ("E106", "Salma Ibrahim", "Pharmacist"),
    ("E107", "Youssef Mahmoud", "Senior Pharmacist"),
    ("E108", "Dina Ali", "Pharmacy Tech"),
    ("E109", "Hassan Rashad", "Pharmacist"),
    ("E110", "Rana Gamal", "Pharmacy Tech"),
)


def _row(rng: random.Random, idx: int, tenant_id: int, today: date) -> dict[str, Any]:
    """Build a single synthetic bronze.sales row."""
    category, brand, products = rng.choice(_CATALOG)
    product = rng.choice(products)
    site_code, site_name = rng.choice(_SITES)
    customer_code, customer_name = rng.choice(_CUSTOMER_NAMES)
    staff_code, staff_name, staff_pos = rng.choice(_STAFF)

    day_offset = rng.randint(0, _DATE_WINDOW_DAYS - 1)
    txn_date = today - timedelta(days=day_offset)

    quantity = rng.choice((1, 1, 1, 2, 2, 3, 5, 10))
    unit_price = round(rng.uniform(8.0, 420.0), 2)
    net_sales = round(unit_price * quantity, 2)
    tax_rate = rng.choice((0.0, 0.05, 0.14))
    tax = round(net_sales * tax_rate, 2)
    gross_sales = round(net_sales + tax, 2)
    discount = round(rng.uniform(0, net_sales * 0.1), 2) if rng.random() < 0.2 else 0.0

    return {
        "tenant_id": tenant_id,
        "source_file": SAMPLE_SOURCE_FILE,
        "source_quarter": SAMPLE_SOURCE_QUARTER,
        "reference_no": f"SMP-{tenant_id:03d}-{idx:07d}",
        "date": txn_date,
        "billing_document": f"BILL-{idx:07d}",
        "billing_type": rng.choice(("CASH", "INSURANCE", "INVOICE")),
        "billing_type2": "STANDARD",
        "material": f"MAT-{abs(hash(product)) % 100000:05d}",
        "material_desc": product,
        "brand": brand,
        "category": category,
        "subcategory": category,
        "division": "RETAIL",
        "segment": "OUTPATIENT",
        "mat_group": category.upper(),
        "mat_group_short": category[:3].upper(),
        "customer": customer_code,
        "customer_name": customer_name,
        "site": site_code,
        "site_name": site_name,
        "buyer": customer_code,
        "personel_number": staff_code,
        "person_name": staff_name,
        "position": staff_pos,
        "quantity": quantity,
        "net_sales": net_sales,
        "gross_sales": gross_sales,
        "sales_not_tax": net_sales,
        "dis_tax": discount,
        "tax": tax,
        "paid": gross_sales,
    }


def build_sample_rows(
    *,
    row_count: int = _DEFAULT_ROW_COUNT,
    tenant_id: int = 1,
    seed: int = 42,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Deterministically generate *row_count* synthetic bronze.sales rows.

    Same seed → byte-identical rows. Safe to call repeatedly for idempotent
    reloads and for reproducible snapshot tests.
    """
    rng = random.Random(seed)
    ref_today = today or date.today()
    return [_row(rng, idx, tenant_id, ref_today) for idx in range(row_count)]


def clear_sample_rows(session: Session, *, tenant_id: int) -> int:
    """Delete any existing sample rows for *tenant_id*. Returns count deleted.

    Scoped to `source_file='sample.csv' AND source_quarter='SAMPLE'`, so
    real imports are never touched.
    """
    stmt = text("""
        DELETE FROM bronze.sales
        WHERE tenant_id = :tenant_id
          AND source_file = :source_file
          AND source_quarter = :source_quarter
    """)
    result = session.execute(
        stmt,
        {
            "tenant_id": tenant_id,
            "source_file": SAMPLE_SOURCE_FILE,
            "source_quarter": SAMPLE_SOURCE_QUARTER,
        },
    )
    deleted = int(getattr(result, "rowcount", 0) or 0)
    log.info("sample_rows_cleared", tenant_id=tenant_id, deleted=deleted)
    return deleted


_INSERT_SQL = text("""
    INSERT INTO bronze.sales (
        tenant_id, source_file, source_quarter,
        reference_no, date,
        billing_document, billing_type, billing_type2,
        material, material_desc, brand,
        category, subcategory, division, segment,
        mat_group, mat_group_short,
        customer, customer_name, site, site_name, buyer,
        personel_number, person_name, position,
        quantity, net_sales, gross_sales, sales_not_tax,
        dis_tax, tax, paid
    ) VALUES (
        :tenant_id, :source_file, :source_quarter,
        :reference_no, :date,
        :billing_document, :billing_type, :billing_type2,
        :material, :material_desc, :brand,
        :category, :subcategory, :division, :segment,
        :mat_group, :mat_group_short,
        :customer, :customer_name, :site, :site_name, :buyer,
        :personel_number, :person_name, :position,
        :quantity, :net_sales, :gross_sales, :sales_not_tax,
        :dis_tax, :tax, :paid
    )
""")


def insert_sample_rows(
    session: Session,
    rows: list[dict[str, Any]],
    *,
    tenant_id: int,
) -> int:
    """Insert *rows* in batches against `bronze.sales`. Returns count inserted.

    Refuses if any row's ``tenant_id`` differs from the caller's — defence
    in depth against accidental cross-tenant writes.
    """
    if not rows:
        return 0
    for row in rows:
        if row.get("tenant_id") != tenant_id:
            raise ValueError(
                f"tenant_id mismatch: row carries {row.get('tenant_id')!r} "
                f"but caller passed {tenant_id!r}"
            )
    total = 0
    for start in range(0, len(rows), _INSERT_BATCH_SIZE):
        batch = rows[start : start + _INSERT_BATCH_SIZE]
        session.execute(_INSERT_SQL, batch)
        total += len(batch)
    log.info("sample_rows_inserted", tenant_id=tenant_id, inserted=total)
    return total


def load_sample(
    session: Session,
    *,
    tenant_id: int,
    row_count: int = _DEFAULT_ROW_COUNT,
    seed: int = 42,
    today: date | None = None,
) -> int:
    """Idempotent single-call loader: clear any prior sample rows, then insert
    a freshly-generated batch. Returns the count inserted.
    """
    clear_sample_rows(session, tenant_id=tenant_id)
    rows = build_sample_rows(
        row_count=row_count,
        tenant_id=tenant_id,
        seed=seed,
        today=today,
    )
    return insert_sample_rows(session, rows, tenant_id=tenant_id)
