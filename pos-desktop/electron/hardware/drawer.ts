/**
 * Real cash drawer adapter — kicks the drawer via the printer's RJ-11 port
 * using the ESC/POS "open cash drawer" command (ESC p).
 *
 * Most 80mm thermal printers have a built-in RJ-11 drawer port; the drawer
 * is connected to the printer, not the PC. The kick command is sent as part
 * of a print job through the same interface as the printer.
 *
 * Interface string is shared with the printer (read from `printer_interface`
 * settings key). Printer type defaults to EPSON.
 *
 * Design ref: docs/plans/specs/2026-04-17-pos-electron-desktop-design.md §5.
 */

import { ThermalPrinter, PrinterTypes } from "node-thermal-printer";
import type { DrawerAdapter } from "./mock";

function resolveType(raw: string): PrinterTypes {
  return raw.toUpperCase() === "STAR" ? PrinterTypes.STAR : PrinterTypes.EPSON;
}

export class RealDrawer implements DrawerAdapter {
  private readonly interface_: string;
  private readonly type: PrinterTypes;

  constructor(interface_: string, type = "EPSON") {
    this.interface_ = interface_;
    this.type = resolveType(type);
  }

  async open(): Promise<{ success: boolean }> {
    const p = new ThermalPrinter({
      type: this.type,
      interface: this.interface_,
      options: { timeout: 3000 },
    });
    try {
      const connected = await p.isPrinterConnected();
      if (!connected) return { success: false };
      p.openCashDrawer();
      await p.execute();
      p.clear();
      return { success: true };
    } catch {
      return { success: false };
    }
  }
}
