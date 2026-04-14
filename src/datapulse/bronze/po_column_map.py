"""Column name mappings: Excel headers -> bronze.purchase_orders / bronze.po_lines."""

from __future__ import annotations

# PO header sheet: Excel column name -> PostgreSQL column name
PO_HEADER_MAP: dict[str, str] = {
    "PO Number": "po_number",
    "PO Date": "po_date",
    "Supplier Code": "supplier_code",
    "Site Code": "site_code",
    "Status": "status",
    "Expected Date": "expected_date",
    "Notes": "notes",
}

# PO lines sheet: Excel column name -> PostgreSQL column name
PO_LINE_MAP: dict[str, str] = {
    "PO Number": "po_number",
    "Line Number": "line_number",
    "Drug Code": "drug_code",
    "Ordered Quantity": "ordered_quantity",
    "Unit Price": "unit_price",
    "Received Quantity": "received_quantity",
}
