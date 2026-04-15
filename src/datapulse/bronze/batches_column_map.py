"""Column mapping for batch/lot Excel import."""

COLUMN_MAP: dict[str, str] = {
    "Drug Code": "drug_code",
    "Site Code": "site_code",
    "Batch Number": "batch_number",
    "Expiry Date": "expiry_date",
    "Initial Quantity": "initial_quantity",
    "Current Quantity": "current_quantity",
    "Unit Cost": "unit_cost",
    "Status": "status",
    "Notes": "notes",
}
