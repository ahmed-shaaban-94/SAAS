/**
 * Catalog pull worker — downloads products and stock from the server (§6.2).
 *
 * Pull behaviour:
 *   • Products: cursor-based alphabetical scan of dim_product (drug_code cursor).
 *     Full catalog re-scanned every 30 min cadence in background.ts.
 *     When next_cursor is null the scan is complete; cursor resets to null.
 *   • Stock: cursor-based scan of stg_batches ordered by loaded_at.
 *     Active batches only; refreshed every 5 min cadence.
 *   • Both use paginated GET endpoints (limit=200) with Bearer JWT auth.
 *   • Upserts are idempotent — replaying pages is safe.
 */

import type Database from "better-sqlite3";
import { upsertProducts } from "../db/products";
import { upsertStock } from "../db/stock";
import { getSetting } from "../db/settings";
import { getBaseUrl } from "./push";

const PAGE_LIMIT = 200;

// ─────────────────────────────────────────────────────────────
// Wire types (mirror server CatalogProductEntry / CatalogStockEntry)
// ─────────────────────────────────────────────────────────────

interface ServerProductItem {
  drug_code: string;
  drug_name: string;
  drug_brand: string | null;
  drug_cluster: string | null;
  is_controlled: boolean;
  requires_pharmacist: boolean;
  unit_price: string;
  updated_at: string;
}

interface ServerProductPage {
  items: ServerProductItem[];
  next_cursor: string | null;
}

interface ServerStockItem {
  drug_code: string;
  site_code: string;
  batch_number: string;
  quantity: string;
  expiry_date: string | null;
  updated_at: string;
}

interface ServerStockPage {
  items: ServerStockItem[];
  next_cursor: string | null;
}

// ─────────────────────────────────────────────────────────────
// HTTP helper
// ─────────────────────────────────────────────────────────────

async function fetchPage<T>(url: string, jwt: string): Promise<T> {
  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (!resp.ok) {
    throw new Error(`[pull] HTTP ${resp.status} ${resp.statusText} — ${url}`);
  }
  return resp.json() as Promise<T>;
}

// ─────────────────────────────────────────────────────────────
// sync_state helpers
// ─────────────────────────────────────────────────────────────

interface SyncStateRow {
  last_cursor: string | null;
}

function getCursor(db: Database.Database, entity: string): string | null {
  const row = db
    .prepare("SELECT last_cursor FROM sync_state WHERE entity=?")
    .get(entity) as SyncStateRow | undefined;
  return row?.last_cursor ?? null;
}

function saveCursor(db: Database.Database, entity: string, cursor: string | null): void {
  db.prepare(
    `UPDATE sync_state SET last_cursor=?, last_synced_at=? WHERE entity=?`,
  ).run(cursor, new Date().toISOString(), entity);
}

// ─────────────────────────────────────────────────────────────
// Pull workers
// ─────────────────────────────────────────────────────────────

/**
 * Pull all product pages since the stored cursor.
 * Returns total rows upserted across all pages.
 * When the catalog is exhausted, resets cursor to null for the next cycle.
 */
export async function pullProducts(db: Database.Database): Promise<number> {
  const jwt = getSetting(db, "jwt");
  if (!jwt) return 0;

  const baseUrl = getBaseUrl();
  let cursor = getCursor(db, "products");
  let totalPulled = 0;

  for (;;) {
    const params = new URLSearchParams({ limit: String(PAGE_LIMIT) });
    if (cursor) params.set("cursor", cursor);

    const page = await fetchPage<ServerProductPage>(
      `${baseUrl}/api/v1/pos/catalog/products?${params}`,
      jwt,
    );

    if (page.items.length > 0) {
      upsertProducts(db, page.items);
      totalPulled += page.items.length;
    }

    if (!page.next_cursor) {
      saveCursor(db, "products", null);
      break;
    }
    cursor = page.next_cursor;
    saveCursor(db, "products", cursor);
  }

  return totalPulled;
}

/**
 * Pull all active-batch stock pages since the stored cursor.
 * Returns total rows upserted across all pages.
 */
export async function pullStock(db: Database.Database, site?: string): Promise<number> {
  const jwt = getSetting(db, "jwt");
  if (!jwt) return 0;

  const baseUrl = getBaseUrl();
  let cursor = getCursor(db, "stock");
  let totalPulled = 0;

  for (;;) {
    const params = new URLSearchParams({ limit: String(PAGE_LIMIT) });
    if (cursor) params.set("cursor", cursor);
    if (site) params.set("site", site);

    const page = await fetchPage<ServerStockPage>(
      `${baseUrl}/api/v1/pos/catalog/stock?${params}`,
      jwt,
    );

    if (page.items.length > 0) {
      upsertStock(
        db,
        page.items.map((item) => ({
          drug_code: item.drug_code,
          site_code: item.site_code,
          batch_number: item.batch_number,
          quantity: item.quantity,
          expiry_date: item.expiry_date,
          updated_at: item.updated_at,
        })),
      );
      totalPulled += page.items.length;
    }

    if (!page.next_cursor) {
      saveCursor(db, "stock", null);
      break;
    }
    cursor = page.next_cursor;
    saveCursor(db, "stock", cursor);
  }

  return totalPulled;
}

/**
 * Pull both products and stock in sequence.
 * Used by the `sync.pullNow` IPC handler and the background cadence timers.
 */
export async function pullCatalog(
  db: Database.Database,
  entity?: "products" | "stock",
): Promise<{ pulled: number }> {
  let pulled = 0;
  if (!entity || entity === "products") pulled += await pullProducts(db);
  if (!entity || entity === "stock") pulled += await pullStock(db);
  return { pulled };
}
