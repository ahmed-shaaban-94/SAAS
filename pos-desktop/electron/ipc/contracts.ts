/**
 * IPC contracts shared between the Electron main process and the Next.js renderer.
 *
 * The shape of every `window.electronAPI.*` call is declared here so both
 * sides type-check against the same definitions. Runtime validation is done
 * with tiny hand-rolled `validate*` functions so this module has ZERO
 * third-party dependencies — it can be imported from main, renderer, or tests
 * without triggering any npm install.
 *
 * When M2 proper lands, these types can be re-expressed as Zod schemas for
 * stronger runtime validation. For now the canonical TypeScript types are
 * the source of truth.
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §4.3.
 */

// ─────────────────────────────────────────────────────────────
// Domain types (mirror the backend Pydantic models where applicable)
// ─────────────────────────────────────────────────────────────

/** Decimal values cross the IPC boundary as strings to avoid float drift. */
export type DecimalString = string;

export interface Product {
  drug_code: string;
  drug_name: string;
  drug_brand: string | null;
  drug_cluster: string | null;
  is_controlled: boolean;
  requires_pharmacist: boolean;
  unit_price: DecimalString;
  updated_at: string;
}

export interface StockInfo {
  drug_code: string;
  site_code: string;
  batches: Array<{
    batch_number: string;
    quantity: DecimalString;
    expiry_date: string | null;
  }>;
}

export interface CartItem {
  drug_code: string;
  drug_name: string;
  batch_number: string | null;
  expiry_date: string | null;
  quantity: DecimalString;
  unit_price: DecimalString;
  discount: DecimalString;
  line_total: DecimalString;
  is_controlled: boolean;
  pharmacist_id: string | null;
}

export type QueueStatus =
  | "pending"
  | "syncing"
  | "synced"
  | "rejected"
  | "reconciled";

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
  // Full payload/envelope/server_response are lazy-loaded via a separate IPC call.
}

export interface QueueStats {
  pending: number;
  syncing: number;
  rejected: number;
  unresolved: number; // status IN ('pending','syncing','rejected')
  last_sync_at: string | null;
}

export interface ShiftRecord {
  id: number | null;
  local_id: string;
  terminal_id: number;
  staff_id: string;
  site_code: string;
  shift_date: string;
  opened_at: string;
  closed_at: string | null;
  opening_cash: DecimalString;
  closing_cash: DecimalString | null;
  expected_cash: DecimalString | null;
  variance: DecimalString | null;
  pending_close: boolean;
}

export interface ReceiptPayload {
  storeName: string;
  storeAddress: string;
  storePhone: string;
  logoPath: string | null;
  transactionId: number | null;
  receiptNumber: string;
  createdAt: string;
  staffName: string;
  customerName: string | null;
  items: Array<{
    name: string;
    qty: DecimalString;
    unitPrice: DecimalString;
    lineTotal: DecimalString;
    batch: string | null;
    expiry: string | null;
  }>;
  subtotal: DecimalString;
  discount: DecimalString;
  tax: DecimalString;
  total: DecimalString;
  paymentMethod: "cash" | "card" | "insurance" | "mixed";
  cashTendered: DecimalString | null;
  changeDue: DecimalString | null;
  languages: Array<"ar" | "en">;
  currency: "EGP";
  /**
   * §3.6 provisional/confirmed marker printed at the top of the receipt.
   * `provisional` = "PENDING CONFIRMATION" banner; `confirmed` = check mark.
   */
  confirmation: Confirmation;
}

export interface OverrideTokenEnvelope {
  claim: {
    grant_id: string;
    code_id: string;
    tenant_id: number;
    terminal_id: number;
    shift_id: number;
    action:
      | "retry_override"
      | "void"
      | "no_sale"
      | "price_override"
      | "discount_above_limit";
    action_subject_id: string | null;
    consumed_at: string;
  };
  signature: string; // base64-url Ed25519
}

export interface CapabilitiesDoc {
  server_version: string;
  min_client_version: string;
  max_client_version: string | null;
  idempotency: string;
  capabilities: Record<string, boolean>;
  enforced_policies: Record<string, number>;
  tenant_key_endpoint: string;
  device_registration_endpoint: string;
}

// ─────────────────────────────────────────────────────────────
// Electron API surface — one interface per namespace
// ─────────────────────────────────────────────────────────────

export interface ElectronDbApi {
  "products.search"(q: string, limit?: number): Promise<Product[]>;
  "products.byCode"(drugCode: string): Promise<Product | null>;
  "stock.forDrug"(drugCode: string, siteCode: string): Promise<StockInfo>;

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

  "shifts.current"(): Promise<ShiftRecord | null>;
  "shifts.open"(payload: {
    terminal_id: number;
    staff_id: string;
    site_code: string;
    opening_cash: DecimalString;
  }): Promise<ShiftRecord>;
  "shifts.close"(payload: {
    shift_id: number;
    closing_cash: DecimalString;
    notes: string | null;
  }): Promise<ShiftRecord>;

  "settings.get"(key: string): Promise<string | null>;
  "settings.set"(key: string, value: string): Promise<void>;
}

export interface ElectronPrinterApi {
  print(payload: ReceiptPayload): Promise<{ success: boolean; error?: string }>;
  status(): Promise<{ online: boolean; paper: "ok" | "low" | "out"; cover: "closed" | "open" }>;
  testPrint(): Promise<{ success: boolean }>;
}

export interface ElectronDrawerApi {
  open(): Promise<{ success: boolean }>;
}

export interface ElectronSyncApi {
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
}

export interface ElectronAuthzApi {
  currentGrant(): Promise<unknown | null>; // deliberately loose — grant shape is server-owned
  grantState(): Promise<"online" | "offline_valid" | "offline_expired" | "revoked">;
  refreshGrant(): Promise<unknown>; // requires online
  consumeOverrideCode(code: string): Promise<
    | { ok: true; code_id: string; issued_to_staff_id: string | null }
    | { ok: false; reason: string }
  >;
  capabilities(): Promise<CapabilitiesDoc>;
}

export interface ElectronUpdaterApi {
  check(): Promise<{ available: boolean; version?: string }>;
  install(): Promise<void>;
}

export interface ElectronAppApi {
  version(): Promise<string>;
  logsPath(): Promise<string>;
  platform: NodeJS.Platform;
  isElectron: true;
}

/** Fixed schema forwarded from the renderer to Sentry via the
 *  `observability.captureError` IPC channel. No free-form `tags` /
 *  `extra` maps — the renderer cannot stuff arbitrary PII in. */
export interface RendererErrorReport {
  message: string;
  stack?: string;
  /** Short classifier — see allowlist in `observability/sentry.ts`. */
  source?: "error-boundary" | "unhandled-rejection" | "window-error" | "manual";
}

export interface ElectronObservabilityApi {
  /** Forward a soft renderer error (uncaught exception, unhandled
   * rejection, ErrorBoundary catch) to the main-process Sentry SDK.
   * Silently no-ops when crash reporting is disabled. */
  captureError(report: RendererErrorReport): Promise<void>;
}

/**
 * The full surface exposed at `window.electronAPI` in the renderer.
 * Main-process IPC handlers MUST cover every entry; renderer calls MUST
 * match these signatures.
 */
export interface ElectronAPI {
  db: ElectronDbApi;
  printer: ElectronPrinterApi;
  drawer: ElectronDrawerApi;
  sync: ElectronSyncApi;
  authz: ElectronAuthzApi;
  updater: ElectronUpdaterApi;
  app: ElectronAppApi;
  observability: ElectronObservabilityApi;

  /** Scanner events pushed from main → renderer (keyboard-emulation lives
   *  in the renderer, but this hook is reserved for Phase-2 raw-HID
   *  scanners that emit through the main process). */
  onBarcodeScanned(callback: (barcode: string) => void): () => void;
}

// ─────────────────────────────────────────────────────────────
// Lightweight runtime validators (no deps)
// ─────────────────────────────────────────────────────────────

export function isCartItem(x: unknown): x is CartItem {
  if (!x || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.drug_code === "string" &&
    typeof o.drug_name === "string" &&
    typeof o.quantity === "string" &&
    typeof o.unit_price === "string" &&
    typeof o.line_total === "string" &&
    typeof o.is_controlled === "boolean"
  );
}

export function isReceiptPayload(x: unknown): x is ReceiptPayload {
  if (!x || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.storeName === "string" &&
    typeof o.receiptNumber === "string" &&
    Array.isArray(o.items) &&
    (o.items as unknown[]).every(isCartItemReceipt) &&
    typeof o.total === "string" &&
    typeof o.confirmation === "string" &&
    ["provisional", "confirmed", "reconciled"].includes(o.confirmation as string)
  );
}

function isCartItemReceipt(x: unknown): boolean {
  if (!x || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.name === "string" &&
    typeof o.qty === "string" &&
    typeof o.unitPrice === "string" &&
    typeof o.lineTotal === "string"
  );
}

export function isOverrideTokenEnvelope(x: unknown): x is OverrideTokenEnvelope {
  if (!x || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  if (typeof o.signature !== "string" || !o.claim || typeof o.claim !== "object") {
    return false;
  }
  const c = o.claim as Record<string, unknown>;
  return (
    typeof c.grant_id === "string" &&
    typeof c.code_id === "string" &&
    typeof c.tenant_id === "number" &&
    typeof c.terminal_id === "number" &&
    typeof c.action === "string" &&
    ["retry_override", "void", "no_sale", "price_override", "discount_above_limit"].includes(
      c.action as string,
    )
  );
}
