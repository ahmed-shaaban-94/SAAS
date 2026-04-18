"use client";

/**
 * KPI row for dashboard v2 — four stat cards with Fraunces serif values.
 */

interface Kpi {
  label: string;
  value: string;
  delta?: { text: string; tone: "up" | "dn" };
}

const MOCK_KPIS: Kpi[] = [
  { label: "Revenue · month-to-date", value: "EGP 4.72M", delta: { text: "+5% vs plan", tone: "up" } },
  { label: "Gross margin", value: "38.4%", delta: { text: "+0.7 pp MoM", tone: "up" } },
  { label: "Stockouts · 30d", value: "128", delta: { text: "−12% vs last 30d", tone: "up" } },
  { label: "Expiry exposure", value: "EGP 142K", delta: { text: "+EGP 38K WoW", tone: "dn" } },
];

export function KpiRow() {
  return (
    <div className="kpi-row">
      {MOCK_KPIS.map((k) => (
        <div key={k.label} className="kpi">
          <div className="label">{k.label}</div>
          <div className="value tabular">{k.value}</div>
          {k.delta && (
            <div className={`delta ${k.delta.tone}`}>
              {k.delta.tone === "up" ? "▲" : "▼"} {k.delta.text}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
