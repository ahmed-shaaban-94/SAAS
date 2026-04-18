import * as path from "path";
import type Database from "better-sqlite3";
import { openDb, closeDb } from "../../db/connection";
import { applySchema } from "../../db/migrate";
import { getCurrentShift, openShift, closeShift } from "../../db/shifts";

const SCHEMA = path.join(__dirname, "../../db/schema.sql");

function freshDb(): Database.Database {
  const db = openDb(":memory:");
  applySchema(db, SCHEMA);
  return db;
}

describe("shift operations", () => {
  let db: Database.Database;

  beforeEach(() => { db = freshDb(); });
  afterEach(() => closeDb());

  it("getCurrentShift returns null when no shift is open", () => {
    expect(getCurrentShift(db)).toBeNull();
  });

  it("openShift inserts a new shift and returns the record", () => {
    const shift = openShift(db, {
      terminal_id: 1,
      staff_id: "STAFF001",
      site_code: "CAI01",
      opening_cash: "500.00",
    });
    expect(shift.local_id).toBeTruthy();
    expect(shift.terminal_id).toBe(1);
    expect(shift.staff_id).toBe("STAFF001");
    expect(shift.site_code).toBe("CAI01");
    expect(shift.opening_cash).toBe("500.00");
    expect(shift.closed_at).toBeNull();
    expect(shift.pending_close).toBe(false);
  });

  it("getCurrentShift returns the open shift after openShift", () => {
    openShift(db, {
      terminal_id: 1,
      staff_id: "STAFF001",
      site_code: "CAI01",
      opening_cash: "500.00",
    });
    const current = getCurrentShift(db);
    expect(current).not.toBeNull();
    expect(current?.staff_id).toBe("STAFF001");
  });

  it("closeShift updates closing fields", () => {
    const opened = openShift(db, {
      terminal_id: 1,
      staff_id: "STAFF001",
      site_code: "CAI01",
      opening_cash: "500.00",
    });

    // Simulate server assigning an id
    db.prepare("UPDATE shifts_local SET id=101 WHERE local_id=?").run(opened.local_id);

    const closed = closeShift(db, {
      shift_id: 101,
      closing_cash: "480.00",
      notes: "Short by 20",
    });

    expect(closed.closed_at).not.toBeNull();
    expect(closed.closing_cash).toBe("480.00");
    expect(closed.pending_close).toBe(false);
  });

  it("getCurrentShift returns null after closeShift", () => {
    const opened = openShift(db, {
      terminal_id: 1,
      staff_id: "STAFF001",
      site_code: "CAI01",
      opening_cash: "500.00",
    });
    db.prepare("UPDATE shifts_local SET id=101 WHERE local_id=?").run(opened.local_id);
    closeShift(db, { shift_id: 101, closing_cash: "500.00", notes: null });
    expect(getCurrentShift(db)).toBeNull();
  });
});
