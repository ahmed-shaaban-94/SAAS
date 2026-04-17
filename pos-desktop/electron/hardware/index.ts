/**
 * Hardware factory — switches between mock and real adapters based on
 * the `hardware_mode` setting.
 *
 * M2 pre-work only wires up the mock adapters; real adapters
 * (`node-thermal-printer`, `serialport`, `node-hid`) require native-module
 * compilation and land in M2 proper.
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §5.
 */

import {
  type DrawerAdapter,
  type PrinterAdapter,
  createMockHardware,
} from "./mock";

export type HardwareMode = "mock" | "real";

export interface HardwareBundle {
  printer: PrinterAdapter;
  drawer: DrawerAdapter;
  mode: HardwareMode;
}

export function createHardware(mode: HardwareMode = "mock"): HardwareBundle {
  if (mode === "mock") {
    const { printer, drawer } = createMockHardware();
    return { printer, drawer, mode };
  }

  // M2 proper: import "./real" and return its adapters.
  // Placeholder throws until native-module work lands.
  throw new Error(
    "hardware_mode=real is not yet available; set hardware_mode='mock' " +
      "until M2 native-module work (node-thermal-printer + serialport) lands",
  );
}
