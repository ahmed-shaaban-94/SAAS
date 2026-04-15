"""Column mapping for stock adjustments Excel import."""

COLUMN_MAP: dict[str, str] = {
    "Adjustment Date": "adjustment_date",
    "Adjustment Type": "adjustment_type",
    "Drug Code": "drug_code",
    "Site Code": "site_code",
    "Batch Number": "batch_number",
    "Quantity": "quantity",
    "Reason": "reason",
    "Authorized By": "authorized_by",
    "Notes": "notes",
}
