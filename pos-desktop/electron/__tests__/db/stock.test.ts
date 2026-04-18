import * as path from "path";
import type Database from "better-sqlite3";
import { openDb, closeDb } from "../../db/connection";
import { applySchema } from "../../db/migrate";
import { getStockForDrug, upsertStock } from "../../db/stock";
import { upsertProducts } from "../../db/products";

const SCHEMA = path.join(__dirname, "../../db/schema.sql");

function freshDb(): Database.Database {
  const db = openDb(":memory:");
  applySchema(db, SCHEMA);
  return db;
}

describe("stock operations", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = freshDb();
    upsertProducts(db, [
      {
        drug_code: "DRG001",
        drug_name: "Paracetamol",
        drug_brand: null,
        drug_cluster: null,
        is_controlled: false,
        requires_pharmacist: false,
        unit_price: "5.00",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ]);
    upsertStock(db, [
      {
        drug_code: "DRG001",
        site_code: "CAI01",
        batch_number: "B001",
        quantity: "100.000",
        expiry_date: "2027-12-31",
        updated_at: "2026-01-01T00:00:00Z",
      },
      {
        drug_code: "DRG001",
        site_code: "CAI01",
        batch_number: "B002",
        quantity: "50.000",
        expiry_date: null,
        updated_at: "2026-01-01T00:00:00Z",
      },
    ]);
  });

  afterEach(() => closeDb());

  it("returns batches for a drug at a given site", () => {
    const info = getStockForDrug(db, "DRG001", "CAI01");
    expect(info.drug_code).toBe("DRG001");
    expect(info.site_code).toBe("CAI01");
    expect(info.batches).toHaveLength(2);
  });

  it("returns batch quantities as decimal strings", () => {
    const info = getStockForDrug(db, "DRG001", "CAI01");
    expect(info.batches[0].quantity).toMatch(/^\d+\.\d+$/);
  });

  it("returns empty batches for unknown drug/site", () => {
    const info = getStockForDrug(db, "DRG999", "CAI01");
    expect(info.batches).toHaveLength(0);
  });

  it("upsertStock updates existing batch", () => {
    upsertStock(db, [
      {
        drug_code: "DRG001",
        site_code: "CAI01",
        batch_number: "B001",
        quantity: "75.000",
        expiry_date: "2027-12-31",
        updated_at: "2026-06-01T00:00:00Z",
      },
    ]);
    const info = getStockForDrug(db, "DRG001", "CAI01");
    const b001 = info.batches.find((b) => b.batch_number === "B001");
    expect(b001?.quantity).toBe("75.000");
  });

  it("null expiry_date is preserved", () => {
    const info = getStockForDrug(db, "DRG001", "CAI01");
    const b002 = info.batches.find((b) => b.batch_number === "B002");
    expect(b002?.expiry_date).toBeNull();
  });
});
