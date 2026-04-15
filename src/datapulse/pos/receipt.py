"""Receipt generation for the POS module.

Generates two formats:
- **Thermal** (ESC/POS byte sequence): for physical receipt printers.
- **PDF** (reportlab): for archiving, email attachment, reprinting.

Both functions are pure (no I/O) — they return bytes that the service
layer saves to ``pos.receipts`` or streams to the HTTP client.

ESC/POS reference: https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/
Key commands used:
    ESC @       — Initialize printer
    ESC a N     — Justify: 0=left, 1=center, 2=right
    ESC E N     — Bold: 1=on, 0=off
    ESC ! N     — Character size (bit 4-6=height, bit 0-2=width)
    LF          — Line feed (0x0A)
    GS V 66 N  — Cut paper (partial feed N dots then cut)
"""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from typing import Any

# ---------------------------------------------------------------------------
# ESC/POS constants
# ---------------------------------------------------------------------------

ESC = 0x1B
GS = 0x1D
LF = 0x0A
CR = 0x0D

# Printer width in characters (standard 80mm thermal = 48 chars)
_THERMAL_WIDTH = 48


def _esc(*bytes_: int) -> bytes:
    return bytes([ESC, *bytes_])


def _gs(*bytes_: int) -> bytes:
    return bytes([GS, *bytes_])


INIT = _esc(ord("@"))            # Initialize
ALIGN_LEFT = _esc(ord("a"), 0)
ALIGN_CENTER = _esc(ord("a"), 1)
ALIGN_RIGHT = _esc(ord("a"), 2)
BOLD_ON = _esc(ord("E"), 1)
BOLD_OFF = _esc(ord("E"), 0)
DOUBLE_HEIGHT = _esc(ord("!"), 0x10)
NORMAL_SIZE = _esc(ord("!"), 0x00)
CUT = _gs(ord("V"), 66, 3)  # Partial cut with 3-dot feed


def _line(text: str, *, width: int = _THERMAL_WIDTH) -> bytes:
    """Encode a single line (truncated/padded to width) + LF."""
    line = text[:width].ljust(width)
    return line.encode("ascii", errors="replace") + bytes([LF])


def _two_col(left: str, right: str, *, width: int = _THERMAL_WIDTH) -> bytes:
    """Format a two-column line (label left, value right)."""
    right = right[:20]
    left = left[: width - len(right) - 1]
    gap = width - len(left) - len(right)
    return (left + " " * gap + right).encode("ascii", errors="replace") + bytes([LF])


def _divider(char: str = "-", *, width: int = _THERMAL_WIDTH) -> bytes:
    return (char * width).encode("ascii") + bytes([LF])


# ---------------------------------------------------------------------------
# Thermal receipt
# ---------------------------------------------------------------------------


def generate_thermal_receipt(
    transaction: dict[str, Any],
    items: list[dict[str, Any]],
    payment: dict[str, Any],
    *,
    pharmacy_name: str = "DataPulse Pharmacy",
) -> bytes:
    """Generate an ESC/POS byte sequence for a thermal receipt printer.

    Args:
        transaction:   Dict with keys: id, receipt_number, created_at,
                       site_code, staff_id, grand_total, subtotal,
                       discount_total, tax_total, customer_id (optional).
        items:         List of dicts with keys: drug_name, batch_number,
                       expiry_date (optional), quantity, unit_price,
                       discount, line_total, is_controlled,
                       pharmacist_id (optional).
        payment:       Dict with keys: method, amount_charged, change_due,
                       insurance_no (optional).
        pharmacy_name: Displayed at the top of the receipt.

    Returns:
        Raw ESC/POS bytes ready to send to a compatible thermal printer.
    """
    buf = bytearray()

    # ── Header ──────────────────────────────────────────────────────────────
    buf += INIT
    buf += ALIGN_CENTER
    buf += BOLD_ON + DOUBLE_HEIGHT
    buf += _line(pharmacy_name)
    buf += BOLD_OFF + NORMAL_SIZE

    created_at = transaction.get("created_at", datetime.now())
    if isinstance(created_at, str):
        import contextlib
        with contextlib.suppress(ValueError):
            created_at = datetime.fromisoformat(created_at)
    date_str = (
        created_at.strftime("%Y-%m-%d %H:%M") if hasattr(created_at, "strftime") else str(
            created_at
        )
    )

    buf += _line(date_str)
    receipt_no = str(transaction.get("receipt_number", ""))
    if receipt_no:
        buf += _line(f"Receipt: {receipt_no}")
    site = transaction.get("site_code", "")
    staff = transaction.get("staff_id", "")
    buf += _line(f"Terminal: {site} | Staff: {staff}")

    customer_id = transaction.get("customer_id")
    if customer_id:
        buf += _line(f"Customer: {customer_id}")

    buf += ALIGN_LEFT
    buf += _divider()

    # ── Items ────────────────────────────────────────────────────────────────
    buf += BOLD_ON
    buf += _two_col("ITEM", "TOTAL")
    buf += BOLD_OFF
    buf += _divider()

    for item in items:
        name = str(item.get("drug_name", "Unknown"))[:32]
        line_total = Decimal(str(item.get("line_total", 0)))
        qty = Decimal(str(item.get("quantity", 0)))
        price = Decimal(str(item.get("unit_price", 0)))

        buf += _two_col(name, f"{line_total:.2f}")
        buf += _line(f"  Qty:{qty:.0f} x {price:.2f}")

        batch = item.get("batch_number")
        expiry = item.get("expiry_date")
        if batch:
            expiry_str = f" Exp:{expiry}" if expiry else ""
            buf += _line(f"  Batch:{batch}{expiry_str}")

        if item.get("is_controlled"):
            pharmacist = item.get("pharmacist_id", "")
            buf += _line(f"  [CONTROLLED] Ph:{pharmacist}")

        discount = Decimal(str(item.get("discount", 0)))
        if discount > 0:
            buf += _two_col("  Discount:", f"-{discount:.2f}")

    buf += _divider()

    # ── Totals ───────────────────────────────────────────────────────────────
    subtotal = Decimal(str(transaction.get("subtotal", 0)))
    discount_total = Decimal(str(transaction.get("discount_total", 0)))
    tax_total = Decimal(str(transaction.get("tax_total", 0)))
    grand_total = Decimal(str(transaction.get("grand_total", 0)))

    buf += _two_col("Subtotal:", f"{subtotal:.2f}")
    if discount_total > 0:
        buf += _two_col("Discount:", f"-{discount_total:.2f}")
    if tax_total > 0:
        buf += _two_col("Tax:", f"{tax_total:.2f}")

    buf += BOLD_ON
    buf += _two_col("TOTAL:", f"{grand_total:.2f}")
    buf += BOLD_OFF

    # ── Payment ───────────────────────────────────────────────────────────────
    buf += _divider()
    method = str(payment.get("method", "cash")).upper()
    amount_charged = Decimal(str(payment.get("amount_charged", grand_total)))
    buf += _two_col(f"Payment ({method}):", f"{amount_charged:.2f}")

    change_due = Decimal(str(payment.get("change_due", 0)))
    if change_due > 0:
        buf += _two_col("Change:", f"{change_due:.2f}")

    insurance_no = payment.get("insurance_no")
    if insurance_no:
        buf += _line(f"Insurance: {insurance_no}")

    # ── Footer ───────────────────────────────────────────────────────────────
    buf += _divider()
    buf += ALIGN_CENTER
    buf += _line("Thank you for your purchase!")
    buf += _line("Keep receipt for returns (7 days)")
    buf += bytes([LF, LF, LF])
    buf += CUT

    return bytes(buf)


# ---------------------------------------------------------------------------
# PDF receipt
# ---------------------------------------------------------------------------


def generate_pdf_receipt(
    transaction: dict[str, Any],
    items: list[dict[str, Any]],
    payment: dict[str, Any],
    *,
    pharmacy_name: str = "DataPulse Pharmacy",
) -> bytes:
    """Generate a PDF receipt using reportlab.

    Returns PDF binary suitable for download or email attachment.
    Falls back to a minimal text-based PDF if reportlab is unavailable.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A5
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        # Fallback: minimal text PDF without reportlab
        return _generate_text_pdf(transaction, items, payment, pharmacy_name=pharmacy_name)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A5,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # --- Header ---
    story.append(Paragraph(f"<b>{pharmacy_name}</b>", styles["Title"]))

    created_at = transaction.get("created_at", datetime.now())
    if isinstance(created_at, str):
        import contextlib
        with contextlib.suppress(ValueError):
            created_at = datetime.fromisoformat(created_at)
    date_str = (
        created_at.strftime("%Y-%m-%d %H:%M") if hasattr(created_at, "strftime") else str(
            created_at
        )
    )

    story.append(Paragraph(f"Date: {date_str}", styles["Normal"]))
    receipt_no = transaction.get("receipt_number", "")
    if receipt_no:
        story.append(Paragraph(f"Receipt #: {receipt_no}", styles["Normal"]))
    site = transaction.get("site_code", "")
    staff = transaction.get("staff_id", "")
    story.append(Paragraph(
        f"Terminal: {site} | Staff: {staff}",
        styles["Normal"],
    ))
    customer_id = transaction.get("customer_id")
    if customer_id:
        story.append(Paragraph(f"Customer: {customer_id}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    # --- Items table ---
    accent = colors.HexColor("#4F46E5")
    header_style = [
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]

    table_data = [["Item", "Batch / Exp.", "Qty", "Price", "Total"]]
    for item in items:
        name = str(item.get("drug_name", ""))[:30]
        batch = str(item.get("batch_number") or "")
        expiry = item.get("expiry_date")
        batch_exp = f"{batch}" + (f" {expiry}" if expiry else "")
        qty = Decimal(str(item.get("quantity", 0)))
        price = Decimal(str(item.get("unit_price", 0)))
        total = Decimal(str(item.get("line_total", 0)))
        controlled_marker = " [C]" if item.get("is_controlled") else ""
        table_data.append([
            name + controlled_marker,
            batch_exp[:20],
            f"{qty:.0f}",
            f"{price:.2f}",
            f"{total:.2f}",
        ])

    items_table = Table(
        table_data,
        colWidths=[60 * mm, 35 * mm, 12 * mm, 20 * mm, 20 * mm],
    )
    items_table.setStyle(TableStyle(header_style))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # --- Totals ---
    grand_total = Decimal(str(transaction.get("grand_total", 0)))
    subtotal = Decimal(str(transaction.get("subtotal", 0)))
    discount_total = Decimal(str(transaction.get("discount_total", 0)))
    tax_total = Decimal(str(transaction.get("tax_total", 0)))

    totals_data = [["Subtotal", f"{subtotal:.2f}"]]
    if discount_total > 0:
        totals_data.append(["Discount", f"-{discount_total:.2f}"])
    if tax_total > 0:
        totals_data.append(["Tax", f"{tax_total:.2f}"])
    totals_data.append(["TOTAL", f"{grand_total:.2f}"])

    totals_table = Table(totals_data, colWidths=[120 * mm, 27 * mm])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (-1, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 3 * mm))

    # --- Payment ---
    method = str(payment.get("method", "cash")).upper()
    amount_charged = Decimal(str(payment.get("amount_charged", grand_total)))
    change_due = Decimal(str(payment.get("change_due", 0)))

    payment_lines = [f"Payment method: {method}", f"Amount paid: {amount_charged:.2f}"]
    if change_due > 0:
        payment_lines.append(f"Change due: {change_due:.2f}")
    insurance_no = payment.get("insurance_no")
    if insurance_no:
        payment_lines.append(f"Insurance #: {insurance_no}")

    for line in payment_lines:
        story.append(Paragraph(line, styles["Normal"]))

    # --- Controlled substance note ---
    controlled_items = [i for i in items if i.get("is_controlled")]
    if controlled_items:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(
            "<b>[C] = Controlled Substance</b> — dispensed under pharmacist supervision.",
            styles["Normal"],
        ))
        for item in controlled_items:
            ph = item.get("pharmacist_id", "")
            story.append(Paragraph(
                f"  {item.get('drug_name', '')} — Pharmacist: {ph}",
                styles["Normal"],
            ))

    # --- Footer ---
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        "<i>Thank you for your purchase. For returns, present this receipt within 7 days.</i>",
        styles["Normal"],
    ))

    doc.build(story)
    return buf.getvalue()


def _generate_text_pdf(
    transaction: dict[str, Any],
    items: list[dict[str, Any]],
    payment: dict[str, Any],
    *,
    pharmacy_name: str = "DataPulse Pharmacy",
) -> bytes:
    """Minimal fallback PDF using plain text encoded as a PDF stream.

    Not standards-compliant but produces a viewable file when reportlab
    is unavailable. Production deployments should always have reportlab.
    """
    created_at = transaction.get("created_at", "")
    grand_total = Decimal(str(transaction.get("grand_total", 0)))
    method = str(payment.get("method", "cash")).upper()

    lines = [
        pharmacy_name,
        f"Date: {created_at}",
        f"Receipt: {transaction.get('receipt_number', '')}",
        "-" * 40,
    ]
    for item in items:
        lines.append(
            f"{item.get('drug_name', '')} x{item.get('quantity', 0)} "
            f"= {item.get('line_total', 0):.2f}"
        )
    lines += ["-" * 40, f"TOTAL: {grand_total:.2f}", f"Payment: {method}"]

    content = "\n".join(lines)
    # Encode as a valid (if minimal) PDF
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 << /Type /Font "
        b"/Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
        + b"4 0 obj\n<< /Length "
        + str(len(content) + 20).encode()
        + b" >>\nstream\nBT\n/F1 10 Tf\n50 800 Td\n("
        + content.encode("ascii", errors="replace")
        + b") Tj\nET\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f\n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
    )
    return pdf
