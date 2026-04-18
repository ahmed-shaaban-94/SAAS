import * as path from "path";
import type Database from "better-sqlite3";
import { openDb, closeDb } from "../../db/connection";
import { applySchema } from "../../db/migrate";
import {
  searchProducts,
  getProductByCode,
  upsertProducts,
} from "../../db/products";

const SCHEMA = path.join(__dirname, "../../db/schema.sql");

function freshDb(): Database.Database {
  const db = openDb(":memory:");
  applySchema(db, SCHEMA);
  return db;
}

describe("products queries", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = freshDb();
    upsertProducts(db, [
      {
        drug_code: "DRG001",
        drug_name: "Paracetamol",
        drug_brand: "Tylenol",
        drug_cluster: "Analgesic",
        is_controlled: false,
        requires_pharmacist: false,
        unit_price: "5.00",
        updated_at: "2026-01-01T00:00:00Z",
      },
      {
        drug_code: "DRG002",
        drug_name: "Ibuprofen",
        drug_brand: "Advil",
        drug_cluster: "Analgesic",
        is_controlled: false,
        requires_pharmacist: false,
        unit_price: "8.50",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ]);
  });

  afterEach(() => closeDb());

  describe("searchProducts", () => {
    it("finds a product by name prefix", () => {
      const results = searchProducts(db, "Parac");
      expect(results).toHaveLength(1);
      expect(results[0].drug_code).toBe("DRG001");
    });

    it("finds products by brand", () => {
      const results = searchProducts(db, "Advil");
      expect(results).toHaveLength(1);
      expect(results[0].drug_code).toBe("DRG002");
    });

    it("returns multiple results for common cluster", () => {
      const results = searchProducts(db, "Analgesic");
      expect(results).toHaveLength(2);
    });

    it("respects the limit parameter", () => {
      const results = searchProducts(db, "Analgesic", 1);
      expect(results).toHaveLength(1);
    });

    it("returns empty for no match", () => {
      const results = searchProducts(db, "NonExistentDrug");
      expect(results).toHaveLength(0);
    });

    it("returns empty for blank query", () => {
      expect(searchProducts(db, "")).toHaveLength(0);
      expect(searchProducts(db, "   ")).toHaveLength(0);
    });

    it("maps is_controlled as boolean", () => {
      const results = searchProducts(db, "Parac");
      expect(typeof results[0].is_controlled).toBe("boolean");
      expect(results[0].is_controlled).toBe(false);
    });

    it("maps requires_pharmacist as boolean", () => {
      const results = searchProducts(db, "Parac");
      expect(typeof results[0].requires_pharmacist).toBe("boolean");
    });
  });

  describe("getProductByCode", () => {
    it("retrieves product by code", () => {
      const p = getProductByCode(db, "DRG001");
      expect(p).not.toBeNull();
      expect(p?.drug_name).toBe("Paracetamol");
      expect(p?.unit_price).toBe("5.00");
    });

    it("returns null for unknown code", () => {
      expect(getProductByCode(db, "UNKNOWN")).toBeNull();
    });

    it("maps boolean fields from integer storage", () => {
      const p = getProductByCode(db, "DRG001");
      expect(typeof p?.is_controlled).toBe("boolean");
      expect(typeof p?.requires_pharmacist).toBe("boolean");
    });
  });

  describe("upsertProducts", () => {
    it("inserts new products", () => {
      upsertProducts(db, [
        {
          drug_code: "DRG003",
          drug_name: "Amoxicillin",
          drug_brand: null,
          drug_cluster: "Antibiotic",
          is_controlled: false,
          requires_pharmacist: true,
          unit_price: "12.00",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ]);
      expect(getProductByCode(db, "DRG003")).not.toBeNull();
    });

    it("updates existing products (upsert)", () => {
      upsertProducts(db, [
        {
          drug_code: "DRG001",
          drug_name: "Paracetamol 500mg",
          drug_brand: "Tylenol",
          drug_cluster: "Analgesic",
          is_controlled: false,
          requires_pharmacist: false,
          unit_price: "6.00",
          updated_at: "2026-06-01T00:00:00Z",
        },
      ]);
      const p = getProductByCode(db, "DRG001");
      expect(p?.drug_name).toBe("Paracetamol 500mg");
      expect(p?.unit_price).toBe("6.00");
    });

    it("handles empty array without error", () => {
      expect(() => upsertProducts(db, [])).not.toThrow();
    });
  });
});
