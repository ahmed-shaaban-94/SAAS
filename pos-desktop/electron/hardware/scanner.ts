/**
 * Scanner adapter — keyboard-emulation scanners (the vast majority of USB
 * barcode scanners) work as HID keyboards: every scanned barcode arrives as
 * a sequence of keystrokes followed by Enter. No main-process code is needed;
 * the renderer handles scan detection via `hooks/usePosScanner.ts`.
 *
 * This module is a no-op stub that satisfies the module layout described in
 * the design spec (§3.2) and provides a home for future HID scanners that
 * require a raw USB channel (node-hid) rather than keyboard emulation.
 *
 * Design ref: docs/plans/specs/2026-04-17-pos-electron-desktop-design.md §5.
 */

export interface ScannerAdapter {
  /** Start listening for barcode events (keyboard-emulation: noop). */
  start(): void;
  /** Stop listening (keyboard-emulation: noop). */
  stop(): void;
}

export class KeyboardEmulationScanner implements ScannerAdapter {
  start(): void {
    // Keyboard-emulation scanners are handled entirely in the renderer.
    // No main-process setup required.
  }

  stop(): void {
    // Nothing to tear down.
  }
}

export function createScanner(): ScannerAdapter {
  return new KeyboardEmulationScanner();
}
