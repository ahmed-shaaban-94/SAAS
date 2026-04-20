import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { act } from "react";

import { useRendererCrashBridge } from "@/hooks/use-renderer-crash-bridge";

describe("useRendererCrashBridge", () => {
  const captureError = vi.fn();
  const originalElectronAPI = (
    window as unknown as { electronAPI?: unknown }
  ).electronAPI;

  beforeEach(() => {
    captureError.mockReset();
  });

  afterEach(() => {
    // Restore whatever was on window before each test ran.
    (window as unknown as { electronAPI?: unknown }).electronAPI =
      originalElectronAPI;
  });

  function installBridge(): void {
    (window as unknown as { electronAPI?: unknown }).electronAPI = {
      app: { isElectron: true, platform: "win32" },
      observability: {
        captureError: (p: unknown) => {
          captureError(p);
          return Promise.resolve();
        },
      },
    };
  }

  function removeBridge(): void {
    delete (window as unknown as { electronAPI?: unknown }).electronAPI;
  }

  it("no-ops when window.electronAPI is undefined (SaaS web)", () => {
    removeBridge();
    const { unmount } = renderHook(() => useRendererCrashBridge());
    act(() => {
      window.dispatchEvent(new ErrorEvent("error", { message: "x" }));
    });
    expect(captureError).not.toHaveBeenCalled();
    unmount();
  });

  it("no-ops when observability.captureError is missing (older POS build)", () => {
    (window as unknown as { electronAPI?: unknown }).electronAPI = {
      app: { isElectron: true, platform: "win32" },
      // no observability key
    };
    renderHook(() => useRendererCrashBridge());
    act(() => {
      window.dispatchEvent(new ErrorEvent("error", { message: "ignored" }));
    });
    expect(captureError).not.toHaveBeenCalled();
  });

  it("forwards window 'error' events as source=window-error", () => {
    installBridge();
    renderHook(() => useRendererCrashBridge());
    const err = new Error("boom");
    act(() => {
      window.dispatchEvent(
        new ErrorEvent("error", { message: "boom", error: err }),
      );
    });
    expect(captureError).toHaveBeenCalledTimes(1);
    const payload = captureError.mock.calls[0][0];
    expect(payload).toMatchObject({
      message: "boom",
      source: "window-error",
    });
    expect(typeof payload.stack).toBe("string");
  });

  it("forwards unhandledrejection with Error reason", () => {
    installBridge();
    renderHook(() => useRendererCrashBridge());
    const reason = new Error("promise-boom");
    act(() => {
      window.dispatchEvent(
        new (class extends Event {
          reason: unknown;
          promise: Promise<unknown>;
          constructor(r: unknown) {
            super("unhandledrejection");
            this.reason = r;
            // Use a pre-resolved promise so the test fixture itself doesn't
            // leak an actual unhandled rejection into the runner.
            this.promise = Promise.resolve();
          }
        })(reason) as PromiseRejectionEvent,
      );
      // Silence the actual rejection so the test doesn't log warnings.
    });
    expect(captureError).toHaveBeenCalledTimes(1);
    const payload = captureError.mock.calls[0][0];
    expect(payload).toMatchObject({
      message: "promise-boom",
      source: "unhandled-rejection",
    });
    expect(typeof payload.stack).toBe("string");
  });

  it("forwards unhandledrejection with string reason (no stack)", () => {
    installBridge();
    renderHook(() => useRendererCrashBridge());
    act(() => {
      window.dispatchEvent(
        new (class extends Event {
          reason: unknown;
          promise: Promise<unknown>;
          constructor(r: unknown) {
            super("unhandledrejection");
            this.reason = r;
            // Use a pre-resolved promise so the test fixture itself doesn't
            // leak an actual unhandled rejection into the runner.
            this.promise = Promise.resolve();
          }
        })("plain string rejection") as PromiseRejectionEvent,
      );
    });
    expect(captureError).toHaveBeenCalledTimes(1);
    const payload = captureError.mock.calls[0][0];
    expect(payload.message).toBe("plain string rejection");
    expect(payload.source).toBe("unhandled-rejection");
    expect(payload.stack).toBeUndefined();
  });

  it("removes listeners on unmount so stale handlers don't fire", () => {
    installBridge();
    const { unmount } = renderHook(() => useRendererCrashBridge());
    unmount();
    act(() => {
      window.dispatchEvent(new ErrorEvent("error", { message: "after" }));
    });
    expect(captureError).not.toHaveBeenCalled();
  });

  it("swallows a rejected IPC invoke — capture path never throws", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    (window as unknown as { electronAPI?: unknown }).electronAPI = {
      app: { isElectron: true, platform: "win32" },
      observability: {
        captureError: () => Promise.reject(new Error("ipc down")),
      },
    };
    renderHook(() => useRendererCrashBridge());
    // Dispatching should NOT throw even though the IPC promise rejects.
    expect(() => {
      act(() => {
        window.dispatchEvent(new ErrorEvent("error", { message: "x" }));
      });
    }).not.toThrow();
    warn.mockRestore();
  });
});
