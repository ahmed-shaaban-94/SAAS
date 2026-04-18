"use client";

/**
 * Money Map — branches rendered as living orbs on an abstract country shape.
 *
 * Size of the orb = revenue bucket (small / medium / large).
 * Color of the orb = margin health: green (healthy) / amber (watchlist) /
 *                    red (at risk) / blue (neutral baseline).
 *
 * Each orb pulses at the tempo of its revenue — tickRate is a ms interval
 * derived from revenue so bigger branches pulse faster.
 */

import { useEffect, useState } from "react";

interface BranchOrb {
  id: string;
  name: string;
  cx: number; // 0-300 viewport x
  cy: number; // 0-180 viewport y
  revenueBucket: "s" | "m" | "l";
  health: "green" | "amber" | "red" | "blue";
  tickMs: number;
}

// Mock data — these are the 24 branches spread across an abstract country outline.
const ORBS: BranchOrb[] = [
  { id: "b1", name: "Maadi", cx: 160, cy: 92, revenueBucket: "l", health: "red", tickMs: 700 },
  { id: "b2", name: "Alex-Main", cx: 80, cy: 58, revenueBucket: "l", health: "green", tickMs: 650 },
  { id: "b3", name: "Zamalek", cx: 148, cy: 80, revenueBucket: "m", health: "green", tickMs: 900 },
  { id: "b4", name: "Nasr City", cx: 180, cy: 75, revenueBucket: "m", health: "blue", tickMs: 1000 },
  { id: "b5", name: "Heliopolis", cx: 192, cy: 62, revenueBucket: "m", health: "green", tickMs: 950 },
  { id: "b6", name: "Giza", cx: 130, cy: 100, revenueBucket: "m", health: "amber", tickMs: 1050 },
  { id: "b7", name: "Tanta", cx: 110, cy: 62, revenueBucket: "s", health: "green", tickMs: 1400 },
  { id: "b8", name: "Mansoura", cx: 138, cy: 48, revenueBucket: "s", health: "blue", tickMs: 1500 },
  { id: "b9", name: "Port Said", cx: 178, cy: 44, revenueBucket: "s", health: "amber", tickMs: 1350 },
  { id: "b10", name: "Aswan", cx: 196, cy: 146, revenueBucket: "s", health: "red", tickMs: 1300 },
  { id: "b11", name: "Luxor", cx: 184, cy: 128, revenueBucket: "s", health: "amber", tickMs: 1400 },
  { id: "b12", name: "Hurghada", cx: 228, cy: 104, revenueBucket: "s", health: "green", tickMs: 1550 },
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
      <circle
        cx={orb.cx}
        cy={orb.cy}
        r={glowR}
        fill={color}
        fillOpacity={pulse ? 0.12 : 0.22}
        style={{ transition: "all 0.4s ease-in-out" }}
      />
      <circle cx={orb.cx} cy={orb.cy} r={r} fill={color} />
      <text
        x={orb.cx}
        y={orb.cy + r + 10}
        textAnchor="middle"
        className="orb-label"
      >
        {orb.name}
      </text>
    </g>
  );
}

export function MoneyMap() {
  return (
    <div className="viz-panel w-span-8">
      <div className="widget-head">
        <span className="tag">06 · MONEY MAP</span>
        <h3>Your branches, as living orbs.</h3>
        <span className="spacer" />
        <span style={{ fontSize: "12px", color: "var(--ink-3)" }}>
          Size = revenue · Color = margin health
        </span>
      </div>

      <div className="money-map-stage">
        <svg viewBox="0 0 300 180" preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%" }}>
          {/* Abstract country outline — stylised, not geographic. */}
          <path
            d="M 40 30 L 260 26 L 272 60 L 262 106 L 232 138 L 200 158 L 130 156 L 80 128 L 50 90 Z"
            fill="rgba(15,42,67,0.45)"
            stroke="rgba(0,199,242,0.25)"
            strokeWidth="1"
            strokeDasharray="3 5"
          />
          {ORBS.map((o) => (
            <Orb key={o.id} orb={o} />
          ))}
        </svg>
      </div>

      <div className="money-map-legend">
        <span className="item">
          <span className="swatch" style={{ background: COLOR.green, color: COLOR.green }} />
          Healthy margin
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
