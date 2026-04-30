/**
 * Mock hardware adapters — swapped in when `settings.hardware_mode === 'mock'`
 * (the default in dev and tests). Every call is recorded in-memory and
 * optionally logged so Playwright E2E scenarios can assert "printer was
 * called with N items" without touching a real device.
 *
 * When M2 proper installs `node-thermal-printer` + `serialport`, a sibling
 * `real.ts` module implements the same interfaces and the factory in
 * `hardware/index.ts` returns one or the other based on the setting.
 *
 * Design ref: docs/plans/specs/2026-04-17-pos-electron-desktop-design.md §5, §9.3.
 */

import type { ReceiptPayload } from "../ipc/contracts";

export interface PrinterAdapter {
  print(payload: ReceiptPayload): Promise<{ success: boolean; error?: string }>;
  status(): Promise<{
    online: boolean;
    paper: "ok" | "low" | "out";
    cover: "closed" | "open";
  }>;
  testPrint(): Promise<{ success: boolean }>;
}

export interface DrawerAdapter {
  open(): Promise<{ success: boolean }>;
}

// ─────────────────────────────────────────────────────────────
// Recorded call log (cleared between test scenarios)
// ─────────────────────────────────────────────────────────────

export interface PrinterCall {
  at: string;
  kind: "print" | "status" | "testPrint";
  payload?: ReceiptPayload;
}

export interface DrawerCall {
  at: string;
  kind: "open";
}

const printerLog: PrinterCall[] = [];
const drawerLog: DrawerCall[] = [];

/** Returns a snapshot + clears the internal log. */
export function takePrinterLog(): PrinterCall[] {
  const out = printerLog.slice();
  printerLog.length = 0;
  return out;
}

export function takeDrawerLog(): DrawerCall[] {
  const out = drawerLog.slice();
  drawerLog.length = 0;
  return out;
}

// ─────────────────────────────────────────────────────────────
// Printer mock
// ─────────────────────────────────────────────────────────────

export class MockPrinter implements PrinterAdapter {
  private paper: "ok" | "low" | "out" = "ok";
  private cover: "closed" | "open" = "closed";
  private online = true;

  async print(payload: ReceiptPayload): Promise<{ success: boolean; error?: string }> {
    printerLog.push({ at: new Date().toISOString(), kind: "print", payload });
    if (!this.online) return { success: false, error: "offline" };
    if (this.cover === "open") return { success: false, error: "cover_open" };
    if (this.paper === "out") return { success: false, error: "paper_out" };
    return { success: true };
  }

  async status() {
    printerLog.push({ at: new Date().toISOString(), kind: "status" });
    return { online: this.online, paper: this.paper, cover: this.cover };
  }

  async testPrint(): Promise<{ success: boolean }> {
    printerLog.push({ at: new Date().toISOString(), kind: "testPrint" });
    return { success: this.online && this.paper !== "out" && this.cover === "closed" };
  }

  // Test-only helpers (not on the PrinterAdapter interface)
  _setPaper(p: "ok" | "low" | "out") { this.paper = p; }
  _setCover(c: "closed" | "open") { this.cover = c; }
  _setOnline(v: boolean) { this.online = v; }
}

// ─────────────────────────────────────────────────────────────
// Drawer mock
// ─────────────────────────────────────────────────────────────

export class MockDrawer implements DrawerAdapter {
  private failures = 0;

  async open(): Promise<{ success: boolean }> {
    drawerLog.push({ at: new Date().toISOString(), kind: "open" });
    if (this.failures > 0) {
      this.failures--;
      return { success: false };
    }
    return { success: true };
  }

  /** Test-only: simulate N consecutive open() failures. */
  _injectFailures(n: number) { this.failures = n; }
}

// ─────────────────────────────────────────────────────────────
// Factory
// ─────────────────────────────────────────────────────────────

export interface MockHardware {
  printer: MockPrinter;
  drawer: MockDrawer;
}

export function createMockHardware(): MockHardware {
  return { printer: new MockPrinter(), drawer: new MockDrawer() };
}
