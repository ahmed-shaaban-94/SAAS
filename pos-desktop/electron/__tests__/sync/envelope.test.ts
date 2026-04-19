import {
  ENVELOPE_VERSION,
  buildCanonicalDigest,
  canonicalString,
  signedAtLooksFresh,
} from "../../sync/envelope";
import type { EnvelopeInput } from "../../sync/envelope";

const BASE_INPUT: EnvelopeInput = {
  method: "POST",
  path: "/api/v1/pos/transactions/commit",
  idempotencyKey: "idem-abc-123",
  terminalId: 7,
  body: '{"items":[]}',
  signedAt: "2026-01-15T12:00:00.000Z",
};

describe("ENVELOPE_VERSION", () => {
  it("is 1", () => {
    expect(ENVELOPE_VERSION).toBe(1);
  });
});

describe("buildCanonicalDigest", () => {
  it("returns a 32-byte Buffer (SHA-256)", () => {
    const digest = buildCanonicalDigest(BASE_INPUT);
    expect(digest).toBeInstanceOf(Buffer);
    expect(digest.length).toBe(32);
  });

  it("same input always produces the same digest (deterministic)", () => {
    const a = buildCanonicalDigest(BASE_INPUT);
    const b = buildCanonicalDigest({ ...BASE_INPUT });
    expect(a.equals(b)).toBe(true);
  });

  it("different path produces a different digest", () => {
    const a = buildCanonicalDigest(BASE_INPUT);
    const b = buildCanonicalDigest({ ...BASE_INPUT, path: "/api/v1/pos/other" });
    expect(a.equals(b)).toBe(false);
  });

  it("different idempotencyKey produces a different digest", () => {
    const a = buildCanonicalDigest(BASE_INPUT);
    const b = buildCanonicalDigest({ ...BASE_INPUT, idempotencyKey: "other-key" });
    expect(a.equals(b)).toBe(false);
  });

  it("different terminalId produces a different digest", () => {
    const a = buildCanonicalDigest(BASE_INPUT);
    const b = buildCanonicalDigest({ ...BASE_INPUT, terminalId: 99 });
    expect(a.equals(b)).toBe(false);
  });

  it("different body produces a different digest", () => {
    const a = buildCanonicalDigest(BASE_INPUT);
    const b = buildCanonicalDigest({ ...BASE_INPUT, body: '{"items":[1]}' });
    expect(a.equals(b)).toBe(false);
  });

  it("body as string vs Uint8Array produces the same digest", () => {
    const bodyStr = '{"hello":"world"}';
    const bodyBytes = new TextEncoder().encode(bodyStr);

    const fromStr = buildCanonicalDigest({ ...BASE_INPUT, body: bodyStr });
    const fromBytes = buildCanonicalDigest({ ...BASE_INPUT, body: bodyBytes });

    expect(fromStr.equals(fromBytes)).toBe(true);
  });

  it("uppercases method before hashing", () => {
    const lower = buildCanonicalDigest({ ...BASE_INPUT, method: "post" });
    const upper = buildCanonicalDigest({ ...BASE_INPUT, method: "POST" });
    expect(lower.equals(upper)).toBe(true);
  });
});

describe("canonicalString", () => {
  it("includes all 6 fields separated by newlines", () => {
    const cs = canonicalString(BASE_INPUT);
    const lines = cs.split("\n");
    expect(lines).toHaveLength(6);
  });

  it("uppercases the method", () => {
    const cs = canonicalString({ ...BASE_INPUT, method: "get" });
    expect(cs.startsWith("GET\n")).toBe(true);
  });

  it("includes the path", () => {
    const cs = canonicalString(BASE_INPUT);
    expect(cs).toContain(BASE_INPUT.path);
  });

  it("includes the idempotencyKey", () => {
    const cs = canonicalString(BASE_INPUT);
    expect(cs).toContain(BASE_INPUT.idempotencyKey);
  });

  it("includes the terminalId as string", () => {
    const cs = canonicalString(BASE_INPUT);
    expect(cs).toContain(String(BASE_INPUT.terminalId));
  });

  it("includes the signedAt", () => {
    const cs = canonicalString(BASE_INPUT);
    expect(cs).toContain(BASE_INPUT.signedAt);
  });

  it("includes a SHA-256 hex body digest (64 hex chars)", () => {
    const cs = canonicalString(BASE_INPUT);
    const lines = cs.split("\n");
    // bodySha is line index 4
    expect(lines[4]).toMatch(/^[0-9a-f]{64}$/);
  });

  it("empty body produces a valid hex body digest", () => {
    const cs = canonicalString({ ...BASE_INPUT, body: "" });
    const lines = cs.split("\n");
    expect(lines[4]).toMatch(/^[0-9a-f]{64}$/);
  });
});

describe("signedAtLooksFresh", () => {
  const now = new Date("2026-01-15T12:00:00.000Z");

  it("returns true for a timestamp exactly at now", () => {
    expect(signedAtLooksFresh(now.toISOString(), now)).toBe(true);
  });

  it("returns true for a timestamp slightly in the past", () => {
    const past = new Date(now.getTime() - 30_000).toISOString(); // 30s ago
    expect(signedAtLooksFresh(past, now)).toBe(true);
  });

  it("returns true for a timestamp within default maxSkew (< 2min future)", () => {
    const slightFuture = new Date(now.getTime() + 60_000).toISOString(); // +1min
    expect(signedAtLooksFresh(slightFuture, now)).toBe(true);
  });

  it("returns true at exactly the maxSkew boundary", () => {
    const boundary = new Date(now.getTime() + 2 * 60 * 1000).toISOString();
    expect(signedAtLooksFresh(boundary, now)).toBe(true);
  });

  it("returns false for a timestamp beyond maxSkew in the future", () => {
    const farFuture = new Date(now.getTime() + 3 * 60 * 1000).toISOString(); // +3min
    expect(signedAtLooksFresh(farFuture, now)).toBe(false);
  });

  it("returns false for an unparseable string", () => {
    expect(signedAtLooksFresh("not-a-date", now)).toBe(false);
  });

  it("returns false for an empty string", () => {
    expect(signedAtLooksFresh("", now)).toBe(false);
  });

  it("returns true for far-past timestamp (lower-bound check is server-only)", () => {
    // Past timestamps are valid client-side — server rejects them against grant window.
    const pastTs = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(); // 24h ago
    expect(signedAtLooksFresh(pastTs)).toBe(true);
  });

  it("respects custom maxSkewMs override", () => {
    const slightFuture = new Date(now.getTime() + 5_000).toISOString(); // +5s
    expect(signedAtLooksFresh(slightFuture, now, 10_000)).toBe(true);
    expect(signedAtLooksFresh(slightFuture, now, 1_000)).toBe(false);
  });
});
