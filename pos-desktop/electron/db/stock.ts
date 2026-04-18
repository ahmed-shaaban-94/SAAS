import type Database from "better-sqlite3";
import type { StockInfo } from "../ipc/contracts";

interface StockRow {
  batch_number: string;
  quantity: string;
  expiry_date: string | null;
}

/** Returns all batches for a drug at a given site. */
export function getStockForDrug(
  db: Database.Database,
  drugCode: string,
  siteCode: string,
): StockInfo {
  const rows = db
    .prepare(
      `SELECT batch_number, quantity, expiry_date
       FROM stock
       WHERE drug_code = ? AND site_code = ?
       ORDER BY expiry_date ASC NULLS LAST`,
    )
    .all(drugCode, siteCode) as StockRow[];

  return {
    drug_code: drugCode,
    site_code: siteCode,
    batches: rows.map((r) => ({
      batch_number: r.batch_number,
      quantity: r.quantity,
      expiry_date: r.expiry_date,
    })),
  };
}

interface StockUpsertRow {
  drug_code: string;
  site_code: string;
  batch_number: string;
  quantity: string;
  expiry_date: string | null;
  updated_at: string;
}

/** Bulk upsert stock rows from a catalog sync payload. */
export function upsertStock(db: Database.Database, rows: StockUpsertRow[]): void {
  if (rows.length === 0) return;

  const stmt = db.prepare(
    `INSERT INTO stock (drug_code, site_code, batch_number, quantity, expiry_date, updated_at)
     VALUES (?, ?, ?, ?, ?, ?)
     ON CONFLICT(drug_code, site_code, batch_number) DO UPDATE SET
       quantity    = excluded.quantity,
       expiry_date = excluded.expiry_date,
       updated_at  = excluded.updated_at`,
  );

  const upsertAll = db.transaction((items: StockUpsertRow[]) => {
    for (const r of items) {
      stmt.run(
        r.drug_code,
        r.site_code,
        r.batch_number,
        r.quantity,
        r.expiry_date ?? null,
        r.updated_at,
      );
    }
  });

  upsertAll(rows);
}
