/**
 * Real thermal printer adapter — wraps node-thermal-printer for ESC/POS
 * 80mm receipt printers (Epson TM series, Bixolon, Sewoo, etc.).
 *
 * Interface string comes from the `printer_interface` settings key:
 *   - TCP/IP:  "tcp://192.168.1.100:9100"
 *   - USB:     "//./USB001"   (Windows)  or  "/dev/usb/lp0"  (Linux)
 *   - Serial:  "//./COM3"    (Windows)  or  "/dev/ttyS0"   (Linux)
 *
 * Printer type comes from `printer_type` (default: "EPSON").
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §5.
 */

import {
  ThermalPrinter,
  PrinterTypes,
  CharacterSet,
  BreakLine,
} from "node-thermal-printer";
import type { PrinterAdapter } from "./mock";
import type { ReceiptPayload } from "../ipc/contracts";

// ─── helpers ──────────────────────────────────────────────────

function resolveType(raw: string): PrinterTypes {
  return raw.toUpperCase() === "STAR" ? PrinterTypes.STAR : PrinterTypes.EPSON;
}

function pad(text: string, width: number): string {
  return text.length >= width ? text.slice(0, width) : text + " ".repeat(width - text.length);
}

function rjust(text: string, width: number): string {
  return text.length >= width ? text.slice(0, width) : " ".repeat(width - text.length) + text;
}

function cols(left: string, right: string, width = 42): string {
  const gap = width - left.length - right.length;
  return gap > 0 ? left + " ".repeat(gap) + right : left.slice(0, width - right.length - 1) + " " + right;
}

// ─── RealPrinter ──────────────────────────────────────────────

export class RealPrinter implements PrinterAdapter {
  private readonly interface_: string;
  private readonly type: PrinterTypes;

  constructor(interface_: string, type = "EPSON") {
    this.interface_ = interface_;
    this.type = resolveType(type);
  }

  private makePrinter(): ThermalPrinter {
    return new ThermalPrinter({
      type: this.type,
      interface: this.interface_,
      characterSet: CharacterSet.PC437_USA,
      removeSpecialCharacters: false,
      lineCharacter: "-",
      breakLine: BreakLine.WORD,
      options: { timeout: 5000 },
    });
  }

  async print(payload: ReceiptPayload): Promise<{ success: boolean; error?: string }> {
    const p = this.makePrinter();
    try {
      const connected = await p.isPrinterConnected();
      if (!connected) return { success: false, error: "printer_offline" };

      // ── Header ────────────────────────────────────────────────
      p.alignCenter();
      p.bold(true);
      p.println(payload.storeName);
      p.bold(false);
      if (payload.storeAddress) p.println(payload.storeAddress);
      if (payload.storePhone) p.println(payload.storePhone);
      p.drawLine();

      // ── Confirmation banner ───────────────────────────────────
      p.bold(true);
      if (payload.confirmation === "confirmed") {
        p.println("✓ CONFIRMED");
      } else if (payload.confirmation === "reconciled") {
        p.println("✓ RECONCILED");
      } else {
        p.println("PENDING CONFIRMATION");
      }
      p.bold(false);
      p.drawLine();

      // ── Meta ──────────────────────────────────────────────────
      p.alignLeft();
      p.println(`Receipt: ${payload.receiptNumber}`);
      p.println(`Date:    ${new Date(payload.createdAt).toLocaleString("en-EG")}`);
      p.println(`Staff:   ${payload.staffName}`);
      if (payload.customerName) p.println(`Customer: ${payload.customerName}`);
      p.drawLine();

      // ── Items ─────────────────────────────────────────────────
      for (const item of payload.items) {
        const nameCol = pad(item.name, 24);
        const qtyCol = pad(`x${item.qty}`, 6);
        const priceCol = rjust(item.lineTotal, 10);
        p.println(`${nameCol}${qtyCol}${priceCol}`);
        if (item.batch) p.println(`  Batch: ${item.batch}${item.expiry ? "  Exp:" + item.expiry : ""}`);
      }
      p.drawLine();

      // ── Totals ────────────────────────────────────────────────
      p.println(cols("Subtotal:", payload.subtotal));
      if (Number(payload.discount) > 0) p.println(cols("Discount:", `-${payload.discount}`));
      if (Number(payload.tax) > 0) p.println(cols("Tax:", payload.tax));
      p.bold(true);
      p.println(cols(`Total (${payload.currency}):`, payload.total));
      p.bold(false);

      // ── Payment ───────────────────────────────────────────────
      p.println(cols("Method:", payload.paymentMethod.toUpperCase()));
      if (payload.cashTendered) p.println(cols("Tendered:", payload.cashTendered));
      if (payload.changeDue) p.println(cols("Change:", payload.changeDue));
      p.drawLine();

      // ── Footer ────────────────────────────────────────────────
      p.alignCenter();
      p.println("Thank you for your visit");
      p.println("شكراً لزيارتكم");
      p.cut();

      await p.execute();
      p.clear();
      return { success: true };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { success: false, error: msg };
    }
  }

  async status(): Promise<{ online: boolean; paper: "ok" | "low" | "out"; cover: "closed" | "open" }> {
    const p = this.makePrinter();
    try {
      const online = await p.isPrinterConnected();
      // node-thermal-printer doesn't expose paper/cover status over TCP;
      // for USB/serial it does via getStatus(). We default to "ok" when
      // connected because most ESC/POS printers only push status via DLE EOT.
      return { online, paper: "ok", cover: "closed" };
    } catch {
      return { online: false, paper: "ok", cover: "closed" };
    }
  }

  async testPrint(): Promise<{ success: boolean }> {
    const p = this.makePrinter();
    try {
      const connected = await p.isPrinterConnected();
      if (!connected) return { success: false };
      p.alignCenter();
      p.println("DataPulse POS — Test Print");
      p.println(new Date().toLocaleString("en-EG"));
      p.drawLine();
      p.println("Printer OK");
      p.cut();
      await p.execute();
      p.clear();
      return { success: true };
    } catch {
      return { success: false };
    }
  }
}
