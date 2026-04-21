import { describe, it, expect } from "vitest";
import {
  rankAlerts,
  mergeAttentionAlerts,
  scoreAlert,
  type AttentionAlert,
} from "@/lib/attention-queue";

const nowIso = () => new Date().toISOString();
const hoursAgo = (h: number) =>
  new Date(Date.now() - h * 60 * 60 * 1000).toISOString();

describe("scoreAlert", () => {
  it("weights severity: red=100, amber=50, blue=10", () => {
    const base = { id: "a", type: "anomaly", title: "t", drillHref: "/x" } as const;
    expect(scoreAlert({ ...base, severity: "red" } as AttentionAlert)).toBeGreaterThan(
      scoreAlert({ ...base, severity: "amber" } as AttentionAlert),
    );
    expect(scoreAlert({ ...base, severity: "amber" } as AttentionAlert)).toBeGreaterThan(
      scoreAlert({ ...base, severity: "blue" } as AttentionAlert),
    );
  });

  it("adds impact weight capped at 50 (EGP 500K saturates)", () => {
    const base = {
      id: "a",
      type: "stock" as const,
      severity: "amber" as const,
      title: "t",
      drillHref: "/x",
    };
    const small: AttentionAlert = { ...base, impactEgp: 10_000 };
    const huge: AttentionAlert = { ...base, impactEgp: 10_000_000 };
    expect(scoreAlert(huge) - scoreAlert(small)).toBeCloseTo(49, 0);
  });

  it("adds recency weight up to 15 (detectedAt within 30h)", () => {
    const base = {
      id: "a",
      type: "anomaly" as const,
      severity: "amber" as const,
      title: "t",
      drillHref: "/x",
    };
    const fresh: AttentionAlert = { ...base, detectedAt: nowIso() };
    const stale: AttentionAlert = { ...base, detectedAt: hoursAgo(48) };
    expect(scoreAlert(fresh)).toBeGreaterThan(scoreAlert(stale));
  });
});

describe("rankAlerts", () => {
  it("sorts red before amber before blue", () => {
    const alerts: AttentionAlert[] = [
      { id: "1", type: "stock", severity: "blue", title: "b", drillHref: "/" },
      { id: "2", type: "stock", severity: "red", title: "r", drillHref: "/" },
      { id: "3", type: "stock", severity: "amber", title: "a", drillHref: "/" },
    ];
    expect(rankAlerts(alerts).map((x) => x.severity)).toEqual(["red", "amber", "blue"]);
  });

  it("tie-breaks stably by id", () => {
    const alerts: AttentionAlert[] = [
      { id: "b", type: "anomaly", severity: "amber", title: "x", drillHref: "/" },
      { id: "a", type: "anomaly", severity: "amber", title: "x", drillHref: "/" },
    ];
    expect(rankAlerts(alerts).map((x) => x.id)).toEqual(["a", "b"]);
  });
});

describe("mergeAttentionAlerts", () => {
  it("maps expiry buckets <=30 days into one row per bucket; red if <=14d", () => {
    const calendar = [
      { bucket: "0-7", days_out: 7, exposure_egp: 12_000, batch_count: 3 },
      { bucket: "15-30", days_out: 30, exposure_egp: 8_000, batch_count: 2 },
      { bucket: "31+", days_out: 60, exposure_egp: 99_999, batch_count: 9 },
    ];
    const merged = mergeAttentionAlerts({
      calendar,
      exposure: undefined,
      reorder: [],
      anomalies: [],
      pipeline: null,
    });
    const expiryAlerts = merged.filter((a) => a.type === "expiry");
    expect(expiryAlerts).toHaveLength(2);
    expect(expiryAlerts.find((a) => a.title.includes("7"))?.severity).toBe("red");
    expect(expiryAlerts.find((a) => a.title.includes("30"))?.severity).toBe("amber");
  });

  it("groups reorder alerts by drug_code, red if on_hand<=0, amber otherwise", () => {
    const reorder = [
      { drug_code: "AMX500", drug_name: "Amox", on_hand: 0, reorder_point: 10, site_name: "B1", margin_impact_egp: 500 },
      { drug_code: "AMX500", drug_name: "Amox", on_hand: 0, reorder_point: 10, site_name: "B2", margin_impact_egp: 300 },
      { drug_code: "PAN40", drug_name: "Pan", on_hand: 3, reorder_point: 10, site_name: "B1", margin_impact_egp: 100 },
    ];
    const merged = mergeAttentionAlerts({
      calendar: [],
      exposure: undefined,
      reorder,
      anomalies: [],
      pipeline: null,
    });
    const stockAlerts = merged.filter((a) => a.type === "stock");
    expect(stockAlerts).toHaveLength(2);
    const amx = stockAlerts.find((a) => a.id === "stock-AMX500")!;
    expect(amx.severity).toBe("red");
    expect(amx.where).toBe("2 branches");
    expect(amx.impactEgp).toBe(800);
  });

  it("maps anomaly cards preserving server severity", () => {
    const anomalies = [
      { id: "an1", title: "Revenue dip", severity: "red", impact_egp: 20_000, detected_at: nowIso() },
      { id: "an2", title: "Minor noise", severity: "blue", impact_egp: null, detected_at: nowIso() },
    ];
    const merged = mergeAttentionAlerts({
      calendar: [],
      exposure: undefined,
      reorder: [],
      anomalies,
      pipeline: null,
    });
    expect(merged.filter((a) => a.type === "anomaly")).toHaveLength(2);
  });

  it("surfaces pipeline only when failed or checks_failed>0", () => {
    const merged1 = mergeAttentionAlerts({
      calendar: [],
      exposure: undefined,
      reorder: [],
      anomalies: [],
      pipeline: { last_run: { status: "success", at: nowIso() }, checks_failed: 0 },
    });
    expect(merged1.filter((a) => a.type === "pipeline")).toHaveLength(0);

    const merged2 = mergeAttentionAlerts({
      calendar: [],
      exposure: undefined,
      reorder: [],
      anomalies: [],
      pipeline: { last_run: { status: "failed", at: nowIso() }, checks_failed: 2 },
    });
    expect(merged2.filter((a) => a.type === "pipeline")).toHaveLength(1);
  });

  it("returns empty array when no inputs have data", () => {
    expect(
      mergeAttentionAlerts({
        calendar: [],
        exposure: undefined,
        reorder: [],
        anomalies: [],
        pipeline: null,
      }),
    ).toEqual([]);
  });
});
