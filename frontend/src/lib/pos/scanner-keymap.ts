/**
 * Keyboard-emulation barcode scanner — pure-TS buffer, no dependencies.
 *
 * Most USB barcode scanners ship in HID-keyboard mode: they "type" the
 * barcode followed by Enter. This module attaches to the document
 * keydown stream and distinguishes scanner input from human typing via
 * a simple timing + length heuristic:
 *
 *   - If N or more characters arrive within `interKeyMs` of each other
 *     and the stream ends with Enter, emit the accumulated string as
 *     `onScan(code)`.
 *   - Otherwise, accumulator is cleared whenever a gap exceeds
 *     `interKeyMs` (which filters out human typing).
 *
 * The listener honours a `data-pos-scanner-ignore` attribute on the
 * currently-focused element so the cashier can type freely into a
 * search or discount field without accidentally triggering a scan.
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §5.1.
 */

export interface ScannerConfig {
  /** Minimum number of characters to consider the stream a scan. */
  minLength?: number;
  /** Max gap (ms) between characters inside a single scan. */
  interKeyMs?: number;
  /** Optional: emit on timeout instead of Enter after this many ms. */
  timeoutMs?: number;
}

export interface ScannerHandle {
  /** Detach the listener. */
  stop(): void;
  /** Force-clear the current accumulator (e.g. when focus shifts). */
  reset(): void;
}

export interface ScannerEvents {
  onScan(code: string): void;
  /** Optional: fired when a stream looked like a scan but was too short. */
  onMiss?(partial: string): void;
}

export const DEFAULT_CONFIG: Required<ScannerConfig> = {
  minLength: 4,
  interKeyMs: 50,
  timeoutMs: 0, // 0 = wait for Enter
};

/**
 * Pure state machine used by the hook + the tests. The DOM adapter is in
 * `attachScannerListener` below; this inner engine is framework-free so it
 * can be unit-tested with no DOM.
 */
export class ScannerEngine {
  private buf = "";
  private lastAt = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private cfg: Required<ScannerConfig>;

  constructor(
    private readonly events: ScannerEvents,
    cfg: ScannerConfig = {},
  ) {
    this.cfg = { ...DEFAULT_CONFIG, ...cfg };
  }

  /** Feed a single character event into the engine. `at` in ms epoch. */
  feed(char: string, at: number, isEnter = false): void {
    const gap = at - this.lastAt;
    if (this.buf.length > 0 && gap > this.cfg.interKeyMs) {
      // Human typing / long pause — drop the buffer.
      this.buf = "";
    }

    if (isEnter) {
      this.flush();
      return;
    }

    if (char.length === 1) {
      this.buf += char;
      this.lastAt = at;
      if (this.cfg.timeoutMs > 0) {
        if (this.timer) clearTimeout(this.timer);
        this.timer = setTimeout(() => this.flush(), this.cfg.timeoutMs);
      }
    }
  }

  reset(): void {
    this.buf = "";
    this.lastAt = 0;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private flush(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    const code = this.buf;
    this.buf = "";
    if (code.length >= this.cfg.minLength) {
      this.events.onScan(code);
    } else if (code.length > 0 && this.events.onMiss) {
      this.events.onMiss(code);
    }
  }
}

/**
 * Attach to `document.keydown`. Returns a handle with `stop()` + `reset()`.
 * Skips events whose target has `data-pos-scanner-ignore` set.
 */
export function attachScannerListener(
  events: ScannerEvents,
  cfg: ScannerConfig = {},
): ScannerHandle {
  const engine = new ScannerEngine(events, cfg);

  const handler = (ev: KeyboardEvent) => {
    const target = ev.target as HTMLElement | null;
    if (target?.closest?.("[data-pos-scanner-ignore]")) return;

    if (ev.key === "Enter") {
      engine.feed("", Date.now(), true);
      return;
    }

    // Only single printable characters — ignore Tab, Shift, arrows, etc.
    if (ev.key.length !== 1) return;

    engine.feed(ev.key, Date.now(), false);
  };

  document.addEventListener("keydown", handler, true);

  return {
    stop: () => document.removeEventListener("keydown", handler, true),
    reset: () => engine.reset(),
  };
}
