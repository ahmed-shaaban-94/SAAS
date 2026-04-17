/**
 * Typed renderer-side wrapper over `window.electronAPI`.
 *
 * Importing this module in browser-only code is safe: if Electron isn't
 * present, `hasElectron()` returns false and the `electron.*` helpers
 * throw early with a clear message, letting callers fall back to the HTTP
 * API via `offline-db.ts`.
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §4.3.
 */

// The canonical interface type lives alongside the Electron main process.
// We import it purely as a type here to avoid pulling any Node-only code
// into the browser bundle.
// eslint-disable-next-line @typescript-eslint/consistent-type-imports
import type { ElectronAPI } from "../../../../../pos-desktop/electron/ipc/contracts";

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

export function hasElectron(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.electronAPI !== "undefined" &&
    window.electronAPI.app?.isElectron === true
  );
}

/**
 * Returns a narrowed `ElectronAPI` or throws. Use only inside code paths
 * guarded by `hasElectron()`. Route-level code should prefer the adapter
 * in `offline-db.ts` which selects between IPC and HTTP automatically.
 */
export function electron(): ElectronAPI {
  if (!hasElectron()) {
    throw new Error(
      "Electron API not available — this code must run inside the POS desktop app. " +
        "Use the offline-db adapter to fall back to HTTP in the browser.",
    );
  }
  return window.electronAPI!;
}

// ─────────────────────────────────────────────────────────────
// Convenience typed wrappers — one per namespace
// ─────────────────────────────────────────────────────────────

export const db = {
  products: {
    search: (q: string, limit = 20) => electron().db["products.search"](q, limit),
    byCode: (drugCode: string) => electron().db["products.byCode"](drugCode),
  },
  stock: {
    forDrug: (drugCode: string, siteCode: string) =>
      electron().db["stock.forDrug"](drugCode, siteCode),
  },
  queue: {
    stats: () => electron().db["queue.stats"](),
    pending: () => electron().db["queue.pending"](),
    rejected: () => electron().db["queue.rejected"](),
    reconcile: (
      localId: string,
      kind: "retry_override" | "record_loss" | "corrective_void",
      note: string,
      overrideCode: string | null,
    ) => electron().db["queue.reconcile"](localId, kind, note, overrideCode),
  },
  shifts: {
    current: () => electron().db["shifts.current"](),
    open: (p: Parameters<ElectronAPI["db"]["shifts.open"]>[0]) =>
      electron().db["shifts.open"](p),
    close: (p: Parameters<ElectronAPI["db"]["shifts.close"]>[0]) =>
      electron().db["shifts.close"](p),
  },
  settings: {
    get: (key: string) => electron().db["settings.get"](key),
    set: (key: string, value: string) => electron().db["settings.set"](key, value),
  },
};

export const printer = {
  print: (payload: Parameters<ElectronAPI["printer"]["print"]>[0]) =>
    electron().printer.print(payload),
  status: () => electron().printer.status(),
  testPrint: () => electron().printer.testPrint(),
};

export const drawer = {
  open: () => electron().drawer.open(),
};

export const sync = {
  pushNow: () => electron().sync.pushNow(),
  pullNow: (entity?: "products" | "stock" | "prices") => electron().sync.pullNow(entity),
  state: () => electron().sync.state(),
};

export const authz = {
  currentGrant: () => electron().authz.currentGrant(),
  grantState: () => electron().authz.grantState(),
  refreshGrant: () => electron().authz.refreshGrant(),
  consumeOverrideCode: (code: string) => electron().authz.consumeOverrideCode(code),
  capabilities: () => electron().authz.capabilities(),
};
