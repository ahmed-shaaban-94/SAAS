import {
  QUEUE_STATES,
  UNRESOLVED_STATES,
  isUnresolved,
  confirmationFor,
  isValidTransition,
  nextAttemptAt,
  aggregateStats,
} from "../../sync/queue-state";
import type { QueueStatus } from "../../ipc/contracts";

// ──────────────────────────────────────────────
// Existing tests (kept intact)
// ──────────────────────────────────────────────

describe("isUnresolved", () => {
  it("returns true for pending", () => {
    expect(isUnresolved("pending")).toBe(true);
  });

  it("returns false for synced", () => {
    expect(isUnresolved("synced")).toBe(false);
  });
});

// ──────────────────────────────────────────────
// confirmationFor
// ──────────────────────────────────────────────

describe("confirmationFor", () => {
  it("returns provisional for pending", () => {
    expect(confirmationFor("pending")).toBe("provisional");
  });

  it("returns provisional for syncing", () => {
    expect(confirmationFor("syncing")).toBe("provisional");
  });

  it("returns provisional for rejected", () => {
    expect(confirmationFor("rejected")).toBe("provisional");
  });

  it("returns confirmed for synced", () => {
    expect(confirmationFor("synced")).toBe("confirmed");
  });

  it("returns reconciled for reconciled", () => {
    expect(confirmationFor("reconciled")).toBe("reconciled");
  });
});

// ──────────────────────────────────────────────
// QUEUE_STATES + UNRESOLVED_STATES constants
// ──────────────────────────────────────────────

describe("QUEUE_STATES", () => {
  it("contains all 5 canonical states", () => {
    expect(QUEUE_STATES).toEqual(
      expect.arrayContaining(["pending", "syncing", "synced", "rejected", "reconciled"])
    );
    expect(QUEUE_STATES).toHaveLength(5);
  });
});

describe("UNRESOLVED_STATES", () => {
  it("contains pending, syncing, rejected", () => {
    expect(UNRESOLVED_STATES).toEqual(
      expect.arrayContaining(["pending", "syncing", "rejected"])
    );
    expect(UNRESOLVED_STATES).toHaveLength(3);
  });

  it("does NOT contain synced or reconciled", () => {
    expect(UNRESOLVED_STATES).not.toContain("synced");
    expect(UNRESOLVED_STATES).not.toContain("reconciled");
  });
});

// ──────────────────────────────────────────────
// isValidTransition — valid edges
// ──────────────────────────────────────────────

describe("isValidTransition — valid transitions", () => {
  const validEdges: Array<[QueueStatus, QueueStatus]> = [
    ["pending", "syncing"],
    ["pending", "rejected"],
    ["syncing", "synced"],
    ["syncing", "pending"],
    ["syncing", "rejected"],
    ["rejected", "reconciled"],
    ["rejected", "syncing"],
  ];

  it.each(validEdges)("%s → %s is valid", (from, to) => {
    expect(isValidTransition(from, to)).toBe(true);
  });
});

describe("isValidTransition — same→same is always valid (idempotent)", () => {
  const allStates: QueueStatus[] = ["pending", "syncing", "synced", "rejected", "reconciled"];

  it.each(allStates)("%s → %s is valid (no-op)", (state) => {
    expect(isValidTransition(state, state)).toBe(true);
  });
});

// ──────────────────────────────────────────────
// isValidTransition — invalid edges
// ──────────────────────────────────────────────

describe("isValidTransition — invalid transitions", () => {
  const invalidEdges: Array<[QueueStatus, QueueStatus]> = [
    ["synced", "pending"],
    ["synced", "syncing"],
    ["synced", "rejected"],
    ["synced", "reconciled"],
    ["reconciled", "syncing"],
    ["reconciled", "pending"],
    ["reconciled", "rejected"],
    ["reconciled", "synced"],
    ["pending", "reconciled"],
    ["pending", "synced"],
  ];

  it.each(invalidEdges)("%s → %s is invalid", (from, to) => {
    expect(isValidTransition(from, to)).toBe(false);
  });
});

// ──────────────────────────────────────────────
// nextAttemptAt
// ──────────────────────────────────────────────

describe("nextAttemptAt", () => {
  const anchor = new Date("2026-01-15T12:00:00.000Z");

  it("retryCount=0 → +1s", () => {
    const result = new Date(nextAttemptAt(0, anchor));
    expect(result.getTime() - anchor.getTime()).toBe(1_000);
  });

  it("retryCount=1 → +2s", () => {
    const result = new Date(nextAttemptAt(1, anchor));
    expect(result.getTime() - anchor.getTime()).toBe(2_000);
  });

  it("retryCount=2 → +4s", () => {
    const result = new Date(nextAttemptAt(2, anchor));
    expect(result.getTime() - anchor.getTime()).toBe(4_000);
  });

  it("retryCount=3 → +8s", () => {
    const result = new Date(nextAttemptAt(3, anchor));
    expect(result.getTime() - anchor.getTime()).toBe(8_000);
  });

  it("retryCount=4 → +30s", () => {
    const result = new Date(nextAttemptAt(4, anchor));
    expect(result.getTime() - anchor.getTime()).toBe(30_000);
  });

  it("retryCount=5 → +120s (2min)", () => {
    const result = new Date(nextAttemptAt(5, anchor));
    expect(result.getTime() - anchor.getTime()).toBe(120_000);
  });

  it("retryCount=6 → +300s (5min cap)", () => {
    const result = new Date(nextAttemptAt(6, anchor));
    expect(result.getTime() - anchor.getTime()).toBe(300_000);
  });

  it("retryCount=100 → +300s (5min cap, no overflow)", () => {
    const result = new Date(nextAttemptAt(100, anchor));
    expect(result.getTime() - anchor.getTime()).toBe(300_000);
  });

  it("returns an ISO-8601 string", () => {
    const result = nextAttemptAt(0, anchor);
    expect(() => new Date(result).toISOString()).not.toThrow();
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  });
});

// ──────────────────────────────────────────────
// aggregateStats
// ──────────────────────────────────────────────

describe("aggregateStats", () => {
  it("returns all zeros for empty input", () => {
    expect(aggregateStats([])).toEqual({
      pending: 0,
      syncing: 0,
      rejected: 0,
      unresolved: 0,
    });
  });

  it("counts pending rows correctly", () => {
    const rows = [{ status: "pending" as QueueStatus }, { status: "pending" as QueueStatus }];
    const stats = aggregateStats(rows);
    expect(stats.pending).toBe(2);
    expect(stats.unresolved).toBe(2);
  });

  it("counts syncing rows correctly", () => {
    const rows = [{ status: "syncing" as QueueStatus }];
    const stats = aggregateStats(rows);
    expect(stats.syncing).toBe(1);
    expect(stats.unresolved).toBe(1);
  });

  it("counts rejected rows correctly", () => {
    const rows = [{ status: "rejected" as QueueStatus }];
    const stats = aggregateStats(rows);
    expect(stats.rejected).toBe(1);
    expect(stats.unresolved).toBe(1);
  });

  it("synced and reconciled do not increment unresolved", () => {
    const rows = [
      { status: "synced" as QueueStatus },
      { status: "reconciled" as QueueStatus },
    ];
    const stats = aggregateStats(rows);
    expect(stats.unresolved).toBe(0);
    expect(stats.pending).toBe(0);
    expect(stats.syncing).toBe(0);
    expect(stats.rejected).toBe(0);
  });

  it("handles mixed statuses correctly — unresolved = pending + syncing + rejected", () => {
    const rows = [
      { status: "pending" as QueueStatus },
      { status: "pending" as QueueStatus },
      { status: "syncing" as QueueStatus },
      { status: "rejected" as QueueStatus },
      { status: "synced" as QueueStatus },
      { status: "reconciled" as QueueStatus },
    ];
    const stats = aggregateStats(rows);
    expect(stats.pending).toBe(2);
    expect(stats.syncing).toBe(1);
    expect(stats.rejected).toBe(1);
    expect(stats.unresolved).toBe(4); // 2 + 1 + 1
  });
});
