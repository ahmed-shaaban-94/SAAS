"""Column mapping for stock receipts Excel import."""

COLUMN_MAP: dict[str, str] = {
    "Receipt Date": "receipt_date",
    "Receipt Reference": "receipt_reference",
    "Drug Code": "drug_code",
    "Site Code": "site_code",
    "Batch Number": "batch_number",
    "Expiry Date": "expiry_date",
    "Quantity": "quantity",
    "Unit Cost": "unit_cost",
    "Supplier Code": "supplier_code",
    "PO Reference": "po_reference",
    "Notes": "notes",
}
