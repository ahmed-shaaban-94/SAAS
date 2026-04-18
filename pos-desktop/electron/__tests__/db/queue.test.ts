import * as path from "path";
import type Database from "better-sqlite3";
import { openDb, closeDb } from "../../db/connection";
import { applySchema } from "../../db/migrate";
import {
  enqueueTransaction,
  getPendingQueue,
  getRejectedQueue,
  getQueueStats,
  reconcileTransaction,
  markSyncing,
  markSynced,
  markRejected,
} from "../../db/queue";

const SCHEMA = path.join(__dirname, "../../db/schema.sql");

function freshDb(): Database.Database {
  const db = openDb(":memory:");
  applySchema(db, SCHEMA);
  return db;
}

describe("queue operations", () => {
  let db: Database.Database;

  beforeEach(() => { db = freshDb(); });
  afterEach(() => closeDb());

  describe("enqueueTransaction", () => {
    it("inserts a pending row and returns ids", () => {
      const result = enqueueTransaction(db, {
        endpoint: "/api/v1/pos/transactions/commit",
        payload: { items: [] },
        signed_at: "2026-01-01T00:00:00Z",
        auth_mode: "bearer",
        grant_id: null,
        device_signature: "sig_abc",
      });
      expect(result.local_id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
      );
      expect(result.client_txn_id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
      );
    });

    it("row status is pending, confirmation is provisional", () => {
      const { local_id } = enqueueTransaction(db, {
        endpoint: "/api/v1/pos/transactions/commit",
        payload: {},
        signed_at: "2026-01-01T00:00:00Z",
        auth_mode: "bearer",
        grant_id: null,
        device_signature: "sig",
      });
      const row = db
        .prepare("SELECT status, confirmation FROM transactions_queue WHERE local_id=?")
        .get(local_id) as { status: string; confirmation: string };
      expect(row.status).toBe("pending");
      expect(row.confirmation).toBe("provisional");
    });

    it("serialises payload as JSON string", () => {
      const payload = { drug_code: "DRG001", qty: "2.000" };
      const { local_id } = enqueueTransaction(db, {
        endpoint: "/api",
        payload,
        signed_at: "2026-01-01T00:00:00Z",
        auth_mode: "bearer",
        grant_id: null,
        device_signature: "sig",
      });
      const row = db
        .prepare("SELECT payload FROM transactions_queue WHERE local_id=?")
        .get(local_id) as { payload: string };
      expect(JSON.parse(row.payload)).toEqual(payload);
    });
  });

  describe("getPendingQueue / getRejectedQueue / getQueueStats", () => {
    function insertRow(status: string, id: string) {
      db.prepare(
        `INSERT INTO transactions_queue
         (local_id, client_txn_id, endpoint, payload, status, confirmation,
          signed_at, auth_mode, device_signature, created_at, updated_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?)`,
      ).run(
        id, `ctxn-${id}`, "/api", "{}", status, "provisional",
        "2026-01-01T00:00:00Z", "bearer", "sig",
        "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
      );
    }

    beforeEach(() => {
      insertRow("pending", "p1");
      insertRow("pending", "p2");
      insertRow("rejected", "r1");
      insertRow("synced", "s1");
    });

    it("getPendingQueue returns pending rows only", () => {
      const rows = getPendingQueue(db);
      expect(rows).toHaveLength(2);
      expect(rows.every((r) => r.status === "pending")).toBe(true);
    });

    it("getRejectedQueue returns rejected rows only", () => {
      const rows = getRejectedQueue(db);
      expect(rows).toHaveLength(1);
      expect(rows[0].status).toBe("rejected");
    });

    it("getQueueStats counts correctly", () => {
      const stats = getQueueStats(db);
      expect(stats.pending).toBe(2);
      expect(stats.rejected).toBe(1);
      expect(stats.syncing).toBe(0);
      expect(stats.unresolved).toBe(3);
      // A 'synced' row exists in the seed so last_sync_at is not null
      expect(stats.last_sync_at).not.toBeNull();
    });
  });

  describe("state transitions", () => {
    let localId: string;

    beforeEach(() => {
      ({ local_id: localId } = enqueueTransaction(db, {
        endpoint: "/api",
        payload: {},
        signed_at: "2026-01-01T00:00:00Z",
        auth_mode: "bearer",
        grant_id: null,
        device_signature: "sig",
      }));
    });

    it("markSyncing transitions pending → syncing", () => {
      markSyncing(db, localId);
      const row = db
        .prepare("SELECT status FROM transactions_queue WHERE local_id=?")
        .get(localId) as { status: string };
      expect(row.status).toBe("syncing");
    });

    it("markSynced transitions syncing → synced + sets confirmation=confirmed", () => {
      markSyncing(db, localId);
      markSynced(db, localId, 42, '{"ok":true}');
      const row = db
        .prepare("SELECT status, confirmation, server_id FROM transactions_queue WHERE local_id=?")
        .get(localId) as { status: string; confirmation: string; server_id: number };
      expect(row.status).toBe("synced");
      expect(row.confirmation).toBe("confirmed");
      expect(row.server_id).toBe(42);
    });

    it("markRejected transitions → rejected + records error", () => {
      markSyncing(db, localId);
      markRejected(db, localId, "409 Conflict");
      const row = db
        .prepare("SELECT status, last_error, retry_count FROM transactions_queue WHERE local_id=?")
        .get(localId) as { status: string; last_error: string; retry_count: number };
      expect(row.status).toBe("rejected");
      expect(row.last_error).toBe("409 Conflict");
      expect(row.retry_count).toBe(1);
    });
  });

  describe("reconcileTransaction", () => {
    it("marks a rejected row as reconciled", () => {
      const { local_id } = enqueueTransaction(db, {
        endpoint: "/api",
        payload: {},
        signed_at: "2026-01-01T00:00:00Z",
        auth_mode: "bearer",
        grant_id: null,
        device_signature: "sig",
      });
      // Force to rejected status
      db.prepare("UPDATE transactions_queue SET status='rejected' WHERE local_id=?").run(local_id);

      const result = reconcileTransaction(db, local_id, "record_loss", "Lost in transit", null);
      expect(result.status).toBe("reconciled");
      expect(result.confirmation).toBe("reconciled");
      expect(result.reconciled_at).toBeTruthy();
    });
  });
});
