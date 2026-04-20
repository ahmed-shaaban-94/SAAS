/**
 * Typed renderer-side wrapper over `window.electronAPI`.
 *
 * Importing this module in browser-only code is safe: if Electron isn't
 * present, `hasElectron()` returns false and the `electron.*` helpers
 * throw early with a clear message, letting callers fall back to the HTTP
 * API via `offline-db.ts`.
 *
 * The canonical interface definition lives alongside the Electron main
 * process at `pos-desktop/electron/ipc/contracts.ts`. The frontend Docker
 * build context does not include `pos-desktop/`, so the browser-bundled
 * copy below is duplicated by hand. Both files MUST be kept in sync.
 * M2 proper can introduce a shared-types package + copy-build step to
 * remove this duplication.
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §4.3.
 */

// ─────────────────────────────────────────────────────────────────────
// Minimal renderer-visible mirror of pos-desktop/electron/ipc/contracts
// ─────────────────────────────────────────────────────────────────────

type DecimalString = string;

interface Product {
  drug_code: string;
  drug_name: string;
  drug_brand: string | null;
  drug_cluster: string | null;
  is_controlled: boolean;
  requires_pharmacist: boolean;
  unit_price: DecimalString;
  updated_at: string;
}

export type QueueStatus = "pending" | "syncing" | "synced" | "rejected" | "reconciled";
export type Confirmation = "provisional" | "confirmed" | "reconciled";

export interface QueueRow {
  local_id: string;
  client_txn_id: string;
  endpoint: string;
  status: QueueStatus;
  confirmation: Confirmation;
  retry_count: number;
  last_error: string | null;
  next_attempt_at: string | null;
  signed_at: string;
  created_at: string;
  updated_at: string;
}

interface QueueStats {
  pending: number;
  syncing: number;
  rejected: number;
  unresolved: number;
  last_sync_at: string | null;
}

interface ElectronAPI {
  db: {
    "products.search"(q: string, limit?: number): Promise<Product[]>;
    "products.byCode"(drugCode: string): Promise<Product | null>;
    "stock.forDrug"(drugCode: string, siteCode: string): Promise<unknown>;
    "queue.enqueue"(input: {
      endpoint: string;
      payload: unknown;
      signed_at: string;
      auth_mode: "bearer" | "offline_grant";
      grant_id: string | null;
      device_signature: string;
    }): Promise<{ local_id: string; client_txn_id: string }>;
    "queue.pending"(): Promise<QueueRow[]>;
    "queue.rejected"(): Promise<QueueRow[]>;
    "queue.stats"(): Promise<QueueStats>;
    "queue.reconcile"(
      localId: string,
      kind: "retry_override" | "record_loss" | "corrective_void",
      note: string,
      overrideCode: string | null,
    ): Promise<{
      status: QueueStatus;
      confirmation: Confirmation;
      reconciled_at: string;
    }>;
    "shifts.current"(): Promise<unknown | null>;
    "shifts.open"(payload: {
      terminal_id: number;
      staff_id: string;
      site_code: string;
      opening_cash: DecimalString;
    }): Promise<unknown>;
    "shifts.close"(payload: {
      shift_id: number;
      closing_cash: DecimalString;
      notes: string | null;
    }): Promise<unknown>;
    "settings.get"(key: string): Promise<string | null>;
    "settings.set"(key: string, value: string): Promise<void>;
  };
  printer: {
    print(payload: unknown): Promise<{ success: boolean; error?: string }>;
    status(): Promise<{
      online: boolean;
      paper: "ok" | "low" | "out";
      cover: "closed" | "open";
    }>;
    testPrint(): Promise<{ success: boolean }>;
  };
  drawer: {
    open(): Promise<{ success: boolean }>;
  };
  sync: {
    pushNow(): Promise<{ pushed: number; rejected: number }>;
    pullNow(entity?: "products" | "stock" | "prices"): Promise<{ pulled: number }>;
    state(): Promise<{
      online: boolean;
      last_sync_at: string | null;
      pending: number;
      syncing: number;
      rejected: number;
      unresolved: number;
    }>;
  };
  authz: {
    currentGrant(): Promise<unknown | null>;
    grantState(): Promise<"online" | "offline_valid" | "offline_expired" | "revoked">;
    refreshGrant(): Promise<unknown>;
    consumeOverrideCode(code: string): Promise<
      | { ok: true; code_id: string; issued_to_staff_id: string | null }
      | { ok: false; reason: string }
    >;
    capabilities(): Promise<unknown>;
  };
  updater: {
    check(): Promise<{ available: boolean; version?: string }>;
    install(): Promise<void>;
  };
  app: {
    version(): Promise<string>;
    logsPath(): Promise<string>;
    platform: string;
    isElectron: true;
  };
  /** Renderer-error bridge — forwards soft errors (uncaught exceptions,
   * unhandled promise rejections, ErrorBoundary catches) to the main-
   * process Sentry SDK. Undefined in pre-bridge builds of the POS
   * desktop app and in every SaaS-web deploy. */
  observability?: {
    captureError(report: {
      message: string;
      stack?: string;
      source?: "error-boundary" | "unhandled-rejection" | "window-error" | "manual";
    }): Promise<void>;
  };
  onBarcodeScanned(callback: (barcode: string) => void): () => void;
}

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
