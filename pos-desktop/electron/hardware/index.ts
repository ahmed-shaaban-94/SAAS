/**
 * Hardware factory — returns mock or real adapters based on `hardware_mode`.
 *
 * Real mode requires `printer_interface` and optionally `printer_type` to be
 * set in the SQLite settings table before switching to `hardware_mode=real`.
 *
 * Design ref: docs/plans/specs/2026-04-17-pos-electron-desktop-design.md §5.
 */

import {
  type DrawerAdapter,
  type PrinterAdapter,
  createMockHardware,
} from "./mock";
import { RealPrinter } from "./printer";
import { RealDrawer } from "./drawer";
import { createScanner, type ScannerAdapter } from "./scanner";

export type HardwareMode = "mock" | "real";

export interface HardwareBundle {
  printer: PrinterAdapter;
  drawer: DrawerAdapter;
  scanner: ScannerAdapter;
  mode: HardwareMode;
}

export interface RealHardwareConfig {
  /** e.g. "tcp://192.168.1.100:9100" or "//./COM3" */
  printerInterface: string;
  /** "EPSON" (default) or "STAR" */
  printerType?: string;
}

export function createHardware(
  mode: HardwareMode = "mock",
  config?: RealHardwareConfig,
): HardwareBundle {
  const scanner = createScanner();

  if (mode === "mock") {
    const { printer, drawer } = createMockHardware();
    return { printer, drawer, scanner, mode };
  }

  if (!config?.printerInterface) {
    throw new Error(
      "hardware_mode=real requires printer_interface to be set in settings. " +
        "Configure it via Settings → Hardware before switching to real mode.",
    );
  }

  const printer = new RealPrinter(config.printerInterface, config.printerType);
  const drawer = new RealDrawer(config.printerInterface, config.printerType);
  return { printer, drawer, scanner, mode };
}
