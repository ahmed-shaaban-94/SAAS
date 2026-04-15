"""Column name mapping: Excel header -> bronze.suppliers DB column."""

from __future__ import annotations

# Excel column name -> PostgreSQL column name
COLUMN_MAP: dict[str, str] = {
    "Supplier Code": "supplier_code",
    "Supplier Name": "supplier_name",
    "Contact Name": "contact_name",
    "Contact Phone": "contact_phone",
    "Contact Email": "contact_email",
    "Address": "address",
    "Payment Terms (Days)": "payment_terms_days",
    "Lead Time (Days)": "lead_time_days",
    "Active": "is_active",
    "Notes": "notes",
}
