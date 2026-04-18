/**
 * ScannerEngine unit tests — exercise the state machine directly with
 * synthetic keystroke timings. No DOM involvement.
 */

import { describe, expect, it, vi } from "vitest";

import { DEFAULT_CONFIG, ScannerEngine } from "@/lib/pos/scanner-keymap";

describe("ScannerEngine", () => {
  it("emits a scan when N chars arrive inside the gap window and end in Enter", () => {
    const onScan = vi.fn();
    const engine = new ScannerEngine({ onScan });
    let t = 1_000;
    for (const ch of "ABC12345") {
      engine.feed(ch, t);
      t += 10; // 10 ms per char — well under 50 ms default gap
    }
    engine.feed("", t, true); // Enter
    expect(onScan).toHaveBeenCalledTimes(1);
    expect(onScan).toHaveBeenCalledWith("ABC12345");
  });

  it("discards the buffer when a gap exceeds interKeyMs", () => {
    const onScan = vi.fn();
    const engine = new ScannerEngine({ onScan });
    engine.feed("A", 1_000);
    engine.feed("B", 1_200); // 200 ms gap > 50 ms → reset
    engine.feed("C", 1_205);
    engine.feed("", 1_210, true);
    expect(onScan).not.toHaveBeenCalled();
  });

  it("ignores streams shorter than minLength and calls onMiss", () => {
    const onScan = vi.fn();
    const onMiss = vi.fn();
    const engine = new ScannerEngine({ onScan, onMiss }, { minLength: 5 });
    for (const ch of "AB") {
      engine.feed(ch, 1_000);
    }
    engine.feed("", 1_010, true);
    expect(onScan).not.toHaveBeenCalled();
    expect(onMiss).toHaveBeenCalledWith("AB");
  });

  it("reset() clears the buffer without emitting", () => {
    const onScan = vi.fn();
    const engine = new ScannerEngine({ onScan });
    engine.feed("X", 1_000);
    engine.feed("Y", 1_010);
    engine.reset();
    engine.feed("", 1_020, true);
    expect(onScan).not.toHaveBeenCalled();
  });

  it("default config matches the documented values", () => {
    expect(DEFAULT_CONFIG.minLength).toBe(4);
    expect(DEFAULT_CONFIG.interKeyMs).toBe(50);
    expect(DEFAULT_CONFIG.timeoutMs).toBe(0);
  });

  it("supports timeout-based flush (no Enter required)", async () => {
    vi.useFakeTimers();
    const onScan = vi.fn();
    const engine = new ScannerEngine({ onScan }, { timeoutMs: 80 });

    let t = 1_000;
    for (const ch of "12345") {
      engine.feed(ch, t);
      t += 10;
    }
    // No Enter. Advance the timeout and the engine flushes.
    await vi.advanceTimersByTimeAsync(100);
    expect(onScan).toHaveBeenCalledWith("12345");
    vi.useRealTimers();
  });
});
