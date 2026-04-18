import type Database from "better-sqlite3";
import type { Product } from "../ipc/contracts";

interface ProductRow {
  drug_code: string;
  drug_name: string;
  drug_brand: string | null;
  drug_cluster: string | null;
  is_controlled: number;
  requires_pharmacist: number;
  unit_price: string;
  updated_at: string;
}

function toProduct(row: ProductRow): Product {
  return {
    drug_code: row.drug_code,
    drug_name: row.drug_name,
    drug_brand: row.drug_brand,
    drug_cluster: row.drug_cluster,
    is_controlled: row.is_controlled !== 0,
    requires_pharmacist: row.requires_pharmacist !== 0,
    unit_price: row.unit_price,
    updated_at: row.updated_at,
  };
}

/**
 * Full-text search across drug_name, drug_brand, drug_cluster.
 * Appends '*' for prefix matching so partial queries work.
 * FTS5 index must be populated via upsertProducts() or a manual rebuild.
 */
export function searchProducts(
  db: Database.Database,
  query: string,
  limit = 25,
): Product[] {
  const q = query.trim();
  if (!q) return [];

  const ftsQuery = q.endsWith("*") ? q : `${q}*`;

  try {
    const rows = db
      .prepare(
        `SELECT p.drug_code, p.drug_name, p.drug_brand, p.drug_cluster,
                p.is_controlled, p.requires_pharmacist, p.unit_price, p.updated_at
         FROM products_fts fts
         JOIN products p ON fts.rowid = p.rowid
         WHERE products_fts MATCH ?
         ORDER BY fts.rank
         LIMIT ?`,
      )
      .all(ftsQuery, limit) as ProductRow[];
    return rows.map(toProduct);
  } catch {
    return [];
  }
}

/** Direct lookup by primary key — bypasses FTS. */
export function getProductByCode(
  db: Database.Database,
  drugCode: string,
): Product | null {
  const row = db
    .prepare(
      `SELECT drug_code, drug_name, drug_brand, drug_cluster,
              is_controlled, requires_pharmacist, unit_price, updated_at
       FROM products WHERE drug_code = ?`,
    )
    .get(drugCode) as ProductRow | undefined;
  return row ? toProduct(row) : null;
}

/**
 * Bulk upsert products from a catalog sync payload.
 * Rebuilds the FTS5 index after all rows are inserted.
 */
export function upsertProducts(db: Database.Database, products: Product[]): void {
  if (products.length === 0) return;

  const stmt = db.prepare(
    `INSERT INTO products
       (drug_code, drug_name, drug_brand, drug_cluster,
        is_controlled, requires_pharmacist, unit_price, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(drug_code) DO UPDATE SET
       drug_name           = excluded.drug_name,
       drug_brand          = excluded.drug_brand,
       drug_cluster        = excluded.drug_cluster,
       is_controlled       = excluded.is_controlled,
       requires_pharmacist = excluded.requires_pharmacist,
       unit_price          = excluded.unit_price,
       updated_at          = excluded.updated_at`,
  );

  const insertAll = db.transaction((rows: Product[]) => {
    for (const p of rows) {
      stmt.run(
        p.drug_code,
        p.drug_name,
        p.drug_brand ?? null,
        p.drug_cluster ?? null,
        p.is_controlled ? 1 : 0,
        p.requires_pharmacist ? 1 : 0,
        p.unit_price,
        p.updated_at,
      );
    }
  });

  insertAll(products);

  // Rebuild FTS index from the products content table after bulk load.
  db.exec("INSERT INTO products_fts(products_fts) VALUES('rebuild')");
}
