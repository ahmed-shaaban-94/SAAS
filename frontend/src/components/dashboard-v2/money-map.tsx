"use client";

/**
 * Money Map — branches rendered as living orbs.
 *
 * Size = revenue bucket (small / medium / large)
 * Color = margin health (green / amber / red / blue baseline)
 * Tempo = revenue-proportional pulse (bigger branches pulse faster)
 *
 * Real data: driven by useSites() (RankingResult of branches by revenue).
 * Since we don't yet have per-branch margin, health is inferred from
 * revenue rank (top third = healthy, middle = baseline, bottom = amber,
 * bottom 10% = red).
 *
 * Falls back to mock data when no branches are loaded so the design
 * preview still renders.
 */

import { useEffect, useState, useMemo } from "react";
import { useSites } from "@/hooks/use-sites";
import type { RankingItem } from "@/types/api";

interface BranchOrb {
  id: string;
  name: string;
  cx: number;
  cy: number;
  revenueBucket: "s" | "m" | "l";
  health: "green" | "amber" | "red" | "blue";
  tickMs: number;
  revenueLabel: string;
}

// Deterministic jitter seeded from branch name so layout is stable.
function hashPos(name: string, salt: number): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  return Math.abs((h ^ salt) % 1000) / 1000;
}

function fmtEGP(v: number): string {
  if (v >= 1_000_000) return `EGP ${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `EGP ${(v / 1_000).toFixed(0)}K`;
  return `EGP ${v}`;
}

function branchesToOrbs(items: RankingItem[]): BranchOrb[] {
  if (items.length === 0) return [];
  const sorted = [...items].sort((a, b) => b.value - a.value);
  const topThird = Math.ceil(sorted.length / 3);
  const bottomDecile = Math.max(1, Math.floor(sorted.length * 0.1));
  const max = sorted[0].value;

  return sorted.slice(0, 14).map((item, idx) => {
    // Revenue bucket based on rank percentile.
    const pct = idx / Math.max(1, sorted.length - 1);
    const bucket: "s" | "m" | "l" = pct < 0.25 ? "l" : pct < 0.6 ? "m" : "s";

    // Health by rank position.
    let health: BranchOrb["health"];
    if (idx >= sorted.length - bottomDecile) health = "red";
    else if (idx < topThird) health = "green";
    else if (pct < 0.65) health = "blue";
    else health = "amber";

    // Pulse tempo proportional to revenue share.
    const share = item.value / max;
    const tickMs = Math.round(1600 - 900 * share);

    // Stable scatter on the country outline. cx 40-260, cy 30-150.
    const cx = 50 + hashPos(item.name, 11) * 210;
    const cy = 40 + hashPos(item.name, 37) * 110;

    return {
      id: String(item.key),
      name: item.name.length > 14 ? item.name.slice(0, 12) + "…" : item.name,
      cx,
      cy,
      revenueBucket: bucket,
      health,
      tickMs,
      revenueLabel: fmtEGP(item.value),
    };
  });
}

const MOCK_ORBS: BranchOrb[] = [
  { id: "mock-1", name: "Maadi", cx: 160, cy: 92, revenueBucket: "l", health: "red", tickMs: 700, revenueLabel: "EGP 1.1M" },
  { id: "mock-2", name: "Alex-Main", cx: 80, cy: 58, revenueBucket: "l", health: "green", tickMs: 650, revenueLabel: "EGP 1.3M" },
  { id: "mock-3", name: "Zamalek", cx: 148, cy: 80, revenueBucket: "m", health: "green", tickMs: 900, revenueLabel: "EGP 780K" },
  { id: "mock-4", name: "Nasr City", cx: 180, cy: 75, revenueBucket: "m", health: "blue", tickMs: 1000, revenueLabel: "EGP 650K" },
  { id: "mock-5", name: "Heliopolis", cx: 192, cy: 62, revenueBucket: "m", health: "green", tickMs: 950, revenueLabel: "EGP 690K" },
  { id: "mock-6", name: "Giza", cx: 130, cy: 100, revenueBucket: "m", health: "amber", tickMs: 1050, revenueLabel: "EGP 540K" },
];

const SIZE = { s: 5, m: 8, l: 12 };
const COLOR: Record<BranchOrb["health"], string> = {
  green: "#1dd48b",
  amber: "#ffab3d",
  red: "#ff7b7b",
  blue: "#00c7f2",
};

function Orb({ orb }: { orb: BranchOrb }) {
  const [pulse, setPulse] = useState(false);
  useEffect(() => {
    const id = setInterval(() => setPulse((p) => !p), orb.tickMs);
    return () => clearInterval(id);
  }, [orb.tickMs]);

  const r = SIZE[orb.revenueBucket];
  const glowR = pulse ? r * 2.2 : r * 1.6;
  const color = COLOR[orb.health];

  return (
    <g>
      <title>{`${orb.name} — ${orb.revenueLabel}`}</title>
      <circle
        cx={orb.cx}
        cy={orb.cy}
        r={glowR}
        fill={color}
        fillOpacity={pulse ? 0.12 : 0.22}
        style={{ transition: "all 0.4s ease-in-out" }}
      />
      <circle cx={orb.cx} cy={orb.cy} r={r} fill={color} />
      <text x={orb.cx} y={orb.cy + r + 10} textAnchor="middle" className="orb-label">
        {orb.name}
      </text>
    </g>
  );
}

export function MoneyMap() {
  const { data, isLoading, error } = useSites();
  const orbs = useMemo(() => {
    if (!data?.items?.length) return MOCK_ORBS;
    return branchesToOrbs(data.items);
  }, [data]);
  const usingMock = !data?.items?.length;

  return (
    <div className="viz-panel w-span-8">
      <div className="widget-head">
        <span className="tag">06 · MONEY MAP</span>
        <h3>Your branches, as living orbs.</h3>
        <span className="spacer" />
        <span style={{ fontSize: "12px", color: "var(--ink-3)" }}>
          Size = revenue · Color = margin health
          {isLoading && !data ? " · loading…" : ""}
          {error ? " · offline" : ""}
          {usingMock && !isLoading && !error ? " · preview data" : ""}
        </span>
      </div>

      <div className="money-map-stage">
        <svg viewBox="0 0 300 180" preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%" }}>
          <path
            d="M 40 30 L 260 26 L 272 60 L 262 106 L 232 138 L 200 158 L 130 156 L 80 128 L 50 90 Z"
            fill="rgba(15,42,67,0.45)"
            stroke="rgba(0,199,242,0.25)"
            strokeWidth="1"
            strokeDasharray="3 5"
          />
          {orbs.map((o) => (
            <Orb key={o.id} orb={o} />
          ))}
        </svg>
      </div>

      <div className="money-map-legend">
        <span className="item">
          <span className="swatch" style={{ background: COLOR.green, color: COLOR.green }} />
          Healthy
        </span>
        <span className="item">
          <span className="swatch" style={{ background: COLOR.amber, color: COLOR.amber }} />
          Watchlist
        </span>
        <span className="item">
          <span className="swatch" style={{ background: COLOR.red, color: COLOR.red }} />
          At risk
        </span>
        <span className="item">
          <span className="swatch" style={{ background: COLOR.blue, color: COLOR.blue }} />
          Baseline
        </span>
      </div>
    </div>
  );
}
