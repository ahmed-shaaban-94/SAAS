import { randomUUID } from "node:crypto";
import type Database from "better-sqlite3";
import type { ShiftRecord, DecimalString } from "../ipc/contracts";

interface ShiftRow {
  id: number | null;
  local_id: string;
  terminal_id: number;
  staff_id: string;
  site_code: string;
  shift_date: string;
  opened_at: string;
  closed_at: string | null;
  opening_cash: string;
  closing_cash: string | null;
  expected_cash: string | null;
  variance: string | null;
  pending_close: number;
}

function toShiftRecord(row: ShiftRow): ShiftRecord {
  return {
    id: row.id,
    local_id: row.local_id,
    terminal_id: row.terminal_id,
    staff_id: row.staff_id,
    site_code: row.site_code,
    shift_date: row.shift_date,
    opened_at: row.opened_at,
    closed_at: row.closed_at,
    opening_cash: row.opening_cash,
    closing_cash: row.closing_cash,
    expected_cash: row.expected_cash,
    variance: row.variance,
    pending_close: row.pending_close !== 0,
  };
}

/** Returns the currently open shift (no closed_at), or null. */
export function getCurrentShift(db: Database.Database): ShiftRecord | null {
  const row = db
    .prepare(
      `SELECT id, local_id, terminal_id, staff_id, site_code, shift_date,
              opened_at, closed_at, opening_cash, closing_cash,
              expected_cash, variance, pending_close
       FROM shifts_local
       WHERE closed_at IS NULL
       ORDER BY opened_at DESC
       LIMIT 1`,
    )
    .get() as ShiftRow | undefined;
  return row ? toShiftRecord(row) : null;
}

interface OpenShiftInput {
  terminal_id: number;
  staff_id: string;
  site_code: string;
  opening_cash: DecimalString;
}

/** Open a new shift. Returns the inserted record. */
export function openShift(db: Database.Database, input: OpenShiftInput): ShiftRecord {
  const now = new Date().toISOString();
  const local_id = randomUUID();
  const shift_date = now.slice(0, 10); // YYYY-MM-DD

  db.prepare(
    `INSERT INTO shifts_local
       (local_id, terminal_id, staff_id, site_code, shift_date, opened_at, opening_cash, pending_close)
     VALUES (?, ?, ?, ?, ?, ?, ?, 0)`,
  ).run(local_id, input.terminal_id, input.staff_id, input.site_code, shift_date, now, input.opening_cash);

  const row = db
    .prepare(
      `SELECT id, local_id, terminal_id, staff_id, site_code, shift_date,
              opened_at, closed_at, opening_cash, closing_cash,
              expected_cash, variance, pending_close
       FROM shifts_local WHERE local_id=?`,
    )
    .get(local_id) as ShiftRow;
  return toShiftRecord(row);
}

interface CloseShiftInput {
  shift_id: number;
  closing_cash: DecimalString;
  notes: string | null;
}

/** Close a shift by its server-assigned id. */
export function closeShift(db: Database.Database, input: CloseShiftInput): ShiftRecord {
  const now = new Date().toISOString();
  db.prepare(
    `UPDATE shifts_local
     SET closed_at=?, closing_cash=?, pending_close=0
     WHERE id=?`,
  ).run(now, input.closing_cash, input.shift_id);

  const row = db
    .prepare(
      `SELECT id, local_id, terminal_id, staff_id, site_code, shift_date,
              opened_at, closed_at, opening_cash, closing_cash,
              expected_cash, variance, pending_close
       FROM shifts_local WHERE id=?`,
    )
    .get(input.shift_id) as ShiftRow;
  return toShiftRecord(row);
}
